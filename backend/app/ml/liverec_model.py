"""
LiveRec-style sequential recommender, adapted for SmartCast.

Based on: Rappaz, McAuley, Aberer (RecSys '21) - "Recommendation on
Live-Streaming Platforms: Dynamic Availability and Repeat Consumption"
Reference implementation: https://github.com/JRappaz/liverec

This is a skeleton, not a finished model. The pieces that need real
work from you are marked TODO. Everything else is the architecture
as described in the paper, translated to PyTorch.

Core idea in one sentence: at each step of a user's watch history,
score only the items that were actually LIVE at that timestamp,
take the top-k, run self-attention over just those candidates, and
predict which one the user watched next.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Sequence encoder (SASRec-style) — turns a user's watch history into a
#    hidden state at every position. h_{p-1} is what we use to both select
#    candidates and score them.
# ---------------------------------------------------------------------------
class SequenceEncoder(nn.Module):
    def __init__(self, n_items, hidden_dim=128, max_len=50, n_heads=2, n_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.item_emb = nn.Embedding(n_items + 1, hidden_dim, padding_idx=0)  # 0 = pad/null
        self.pos_emb = nn.Embedding(max_len, hidden_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim, nhead=n_heads, dim_feedforward=hidden_dim * 4,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.dropout = nn.Dropout(dropout)

    def forward(self, item_seq):
        """
        item_seq: (batch, seq_len) of item ids, 0-padded on the left for
        short sequences (matches the paper's padding convention).
        Returns: (batch, seq_len, hidden_dim) hidden states h_p, where
        h_{p-1} is used to predict the p-th entry.
        """
        batch, seq_len = item_seq.shape
        positions = torch.arange(seq_len, device=item_seq.device).unsqueeze(0).expand(batch, -1)

        x = self.item_emb(item_seq) + self.pos_emb(positions)
        x = self.dropout(x)

        # causal mask: position p can't attend to positions > p
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, dtype=torch.bool, device=item_seq.device), diagonal=1
        )
        # True where padded (unused to prevent NaN propagation)
        pad_mask = (item_seq == 0)

        h = self.encoder(x, mask=causal_mask)
        return h


# ---------------------------------------------------------------------------
# 2. Time-interval (repeat consumption) embedding — buckets the recency of
#    a candidate item's last occurrence in the user's history, so the model
#    can distinguish "never seen" from "watched 2 hours ago" from "watched
#    3 weeks ago". Paper uses 24h buckets, clipped at 20 days -> 21 buckets
#    (0 = novel item, no prior occurrence).
# ---------------------------------------------------------------------------
class TimeIntervalEmbedding(nn.Module):
    def __init__(self, hidden_dim=128, n_buckets=21, bucket_hours=24, max_days=20):
        super().__init__()
        self.n_buckets = n_buckets
        self.bucket_hours = bucket_hours
        self.max_days = max_days
        self.emb = nn.Embedding(n_buckets, hidden_dim)

    def bucketize(self, hours_since_last_seen):
        """
        hours_since_last_seen: tensor, -1 for items never seen before.
        Returns bucket indices in [0, n_buckets - 1].
        """
        bucket = torch.zeros_like(hours_since_last_seen, dtype=torch.long)
        seen_mask = hours_since_last_seen >= 0
        days = (hours_since_last_seen / self.bucket_hours).clamp(max=self.max_days).long()
        bucket[seen_mask] = days[seen_mask] + 1  # +1 so index 0 stays reserved for "novel"
        return bucket

    def forward(self, hours_since_last_seen):
        bucket = self.bucketize(hours_since_last_seen)
        return self.emb(bucket)


# ---------------------------------------------------------------------------
# 3. Self-attention block over the top-k available candidates. This is the
#    "av" (availability) module — separate from the causal sequence
#    encoder above, no positions, no causal mask, because candidate order
#    is arbitrary.
# ---------------------------------------------------------------------------
class CandidateAttention(nn.Module):
    def __init__(self, hidden_dim=128, n_heads=2, n_layers=1, dropout=0.2):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim, nhead=n_heads, dim_feedforward=hidden_dim * 4,
            dropout=dropout, batch_first=True,
        )
        self.attn = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

    def forward(self, candidate_embs, pad_mask=None):
        """
        candidate_embs: (batch, k, hidden_dim) — embeddings of the top-k
        available items (already summed with their time-interval embedding
        if using the +rep variant).
        Returns refined (batch, k, hidden_dim) representations.
        """
        return self.attn(candidate_embs, src_key_padding_mask=pad_mask)


# ---------------------------------------------------------------------------
# 4. Full model: wires the three pieces together.
# ---------------------------------------------------------------------------
class LiveRec(nn.Module):
    def __init__(self, n_items, hidden_dim=128, max_len=50, top_k=128,
                 use_repeat=True, use_availability=True):
        super().__init__()
        self.top_k = top_k
        self.use_repeat = use_repeat
        self.use_availability = use_availability

        self.sequence_encoder = SequenceEncoder(n_items, hidden_dim, max_len)
        self.item_emb = self.sequence_encoder.item_emb  # shared embedding table (matrix M in the paper)

        if use_repeat:
            self.time_emb = TimeIntervalEmbedding(hidden_dim)
        if use_availability:
            self.candidate_attn = CandidateAttention(hidden_dim)

    def score_candidates(self, h_prev, candidate_ids, hours_since_last_seen=None, pos_id=None, neg_id=None):
        cand_embs = self.item_emb(candidate_ids)  # (batch, n_available, h)

        if self.use_repeat and hours_since_last_seen is not None:
            cand_embs = cand_embs + self.time_emb(hours_since_last_seen)

        scores = torch.einsum("bh,bnh->bn", h_prev, cand_embs)

        k = min(self.top_k, candidate_ids.size(1))
        top_scores, top_idx = scores.topk(k, dim=1)
        top_ids = candidate_ids.gather(1, top_idx)

        # Force inject pos_id and neg_id into top_ids during training
        if pos_id is not None and neg_id is not None:
            top_idx = top_idx.clone()
            top_ids = top_ids.clone()
            for b in range(candidate_ids.size(0)):
                pid = pos_id[b].item()
                nid = neg_id[b].item()
                # find where pid and nid are in candidate_ids
                pid_idx = (candidate_ids[b] == pid).nonzero(as_tuple=True)[0]
                nid_idx = (candidate_ids[b] == nid).nonzero(as_tuple=True)[0]
                
                if len(pid_idx) > 0 and pid not in top_ids[b]:
                    top_idx[b, -1] = pid_idx[0]
                    top_ids[b, -1] = pid
                if len(nid_idx) > 0 and nid not in top_ids[b]:
                    # inject at -2 to not overwrite the positive if we just put it at -1
                    top_idx[b, -2] = nid_idx[0]
                    top_ids[b, -2] = nid

        top_embs = cand_embs.gather(1, top_idx.unsqueeze(-1).expand(-1, -1, cand_embs.size(-1)))
        return top_ids, top_embs, top_scores, top_idx

    def forward(self, item_seq, candidate_ids, hours_since_last_seen=None, pos_id=None, neg_id=None):
        h = self.sequence_encoder(item_seq)
        h_prev = h[:, -1, :]

        top_ids, top_embs, prelim_scores, top_idx = self.score_candidates(
            h_prev, candidate_ids, hours_since_last_seen, pos_id, neg_id
        )

        if self.use_availability:
            refined = self.candidate_attn(top_embs)
            final_scores = torch.einsum("bh,bkh->bk", h_prev, refined)
        else:
            final_scores = prelim_scores

        return final_scores, top_ids, top_idx


# ---------------------------------------------------------------------------
# 5. Availability-aware negative sampling + loss.
#    TODO: replace this stub with real lookups against your availability
#    matrix (paper: precomputed n_items x n_timesteps matrix; for you,
#    probably a query against Redis/Postgres for "streams live at time t").
# ---------------------------------------------------------------------------
def sample_negative(positive_item, available_items_at_t):
    """
    available_items_at_t: 1D tensor of item ids live at time t (excludes
    the positive item already). Paper samples uniformly from this set
    rather than uniformly over ALL items — that single change was a 21%
    relative improvement in their ablation.
    """
    idx = torch.randint(0, available_items_at_t.size(0), (1,))
    return available_items_at_t[idx]


def bpr_style_loss(pos_scores, neg_scores):
    """Cross-entropy over sigmoid(pos) vs sigmoid(neg), as in the paper's
    training objective (Section 5.4)."""
    # Using log-sigmoid of the difference is more numerically stable
    return -torch.nn.functional.logsigmoid(pos_scores - neg_scores).mean()


# ---------------------------------------------------------------------------
# 6. Minimal training step sketch. Fill in your DataLoader — each batch
#    needs: item_seq, the positive next-item id, the set of items available
#    at that timestep, and (if use_repeat) hours-since-last-seen per item.
# ---------------------------------------------------------------------------
def train_step(model, optimizer, item_seq, positive_ids, available_ids, hours_since_last_seen=None):
    optimizer.zero_grad()

    scores, top_ids = model(item_seq, available_ids, hours_since_last_seen)

    # TODO: find where positive_ids landed in top_ids per row (or force-
    # include the positive in the candidate set before top-k, as the
    # paper effectively guarantees during training).
    pos_mask = (top_ids == positive_ids.unsqueeze(1))
    pos_scores = (scores * pos_mask).sum(dim=1)
    neg_scores = (scores * (~pos_mask)).mean(dim=1)  # crude; paper samples explicit negatives

    loss = bpr_style_loss(pos_scores, neg_scores)
    loss.backward()
    optimizer.step()
    return loss.item()


# ---------------------------------------------------------------------------
# Evaluation metrics: Hit@1, Hit@10, NDCG@10 (paper's Section 6.1), split
# into "new" vs "repeat" hits as in Table 2.
# ---------------------------------------------------------------------------
def hit_at_k(scores, top_ids, true_id, k):
    topk_ids = top_ids.gather(1, scores.topk(k, dim=1).indices)
    return (topk_ids == true_id.unsqueeze(1)).any(dim=1).float()


def ndcg_at_k(scores, top_ids, true_id, k):
    order = scores.topk(k, dim=1).indices
    topk_ids = top_ids.gather(1, order)
    hit_pos = (topk_ids == true_id.unsqueeze(1)).float()
    ranks = torch.arange(1, k + 1, device=scores.device).float()
    dcg = (hit_pos / torch.log2(ranks + 1)).sum(dim=1)
    return dcg  # ideal DCG is 1 for a single relevant item, so this equals NDCG@k here
