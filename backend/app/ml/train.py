import os
import argparse
from pathlib import Path
import json
import pickle
import csv
import numpy as np

os.environ['KMP_DUPLICATE_LIB_OK']='True'

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

import sys
# Make sure we can import liverec_model from the same directory
base_dir = Path(__file__).resolve().parent
sys.path.append(str(base_dir))

from liverec_model import LiveRec, hit_at_k, ndcg_at_k
import warnings
warnings.filterwarnings("ignore")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class LiveRecDataset(Dataset):
    def __init__(self, sequences, availability, max_len=50):
        self.sequences = sequences
        self.availability = availability
        self.max_len = max_len
        self.user_ids = list(sequences.keys())
        
        self.samples = []
        for u in self.user_ids:
            seq = self.sequences[u]
            if len(seq) < 3:
                continue
            
            for i in range(1, len(seq)):
                target_item, target_time = seq[i]
                history = seq[:i]
                self.samples.append((u, history, target_item, target_time))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        u, history, target_item, target_time = self.samples[idx]
        
        item_seq = [item for item, t in history]
        if len(item_seq) >= self.max_len:
            item_seq = item_seq[-self.max_len:]
        else:
            item_seq = [0] * (self.max_len - len(item_seq)) + item_seq
            
        available = list(self.availability.get(target_time, []))
        if target_item not in available:
            available.append(target_item)

        max_cands = 256
        if len(available) > max_cands:
            available = list(np.random.choice(available, max_cands, replace=False))
            if target_item not in available:
                available[0] = target_item

        neg_item = 0
        if len(available) > 1:
            available_set = set(available)
            available_set.discard(target_item)
            if available_set:
                neg_item = np.random.choice(list(available_set))
                
        hours_since = []
        history_dict = {item: t for item, t in history}
        for item in available:
            if item in history_dict:
                hours = (target_time - history_dict[item]) / 6.0
                hours_since.append(hours)
            else:
                hours_since.append(-1.0)
                
        return {
            'item_seq': torch.tensor(item_seq, dtype=torch.long),
            'target_item': torch.tensor(target_item, dtype=torch.long),
            'neg_item': torch.tensor(neg_item, dtype=torch.long),
            'available': torch.tensor(available, dtype=torch.long),
            'hours_since': torch.tensor(hours_since, dtype=torch.float),
            'target_time': torch.tensor(target_time, dtype=torch.long)
        }

def collate_fn(batch):
    item_seq = torch.stack([x['item_seq'] for x in batch])
    target_item = torch.stack([x['target_item'] for x in batch])
    neg_item = torch.stack([x['neg_item'] for x in batch])
    
    max_avail = max([len(x['available']) for x in batch])
    
    batch_available = []
    batch_hours = []
    
    for x in batch:
        avail = x['available']
        hours = x['hours_since']
        pad_len = max_avail - len(avail)
        if pad_len > 0:
            avail = torch.cat([avail, torch.zeros(pad_len, dtype=torch.long)])
            hours = torch.cat([hours, torch.full((pad_len,), -1.0, dtype=torch.float)])
        batch_available.append(avail)
        batch_hours.append(hours)
        
    return {
        'item_seq': item_seq,
        'target_item': target_item,
        'neg_item': neg_item,
        'available': torch.stack(batch_available),
        'hours_since': torch.stack(batch_hours)
    }

class EvalDataset(Dataset):
    def __init__(self, test_samples, availability, max_len=50):
        self.samples = test_samples
        self.availability = availability
        self.max_len = max_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        u, history, target_item, target_time = self.samples[idx]
        
        item_seq = [item for item, t in history]
        if len(item_seq) >= self.max_len:
            item_seq = item_seq[-self.max_len:]
        else:
            item_seq = [0] * (self.max_len - len(item_seq)) + item_seq
            
        available = list(self.availability.get(target_time, []))
        if target_item not in available:
            available.append(target_item)

        max_cands = 256
        if len(available) > max_cands:
            available = list(np.random.choice(available, max_cands, replace=False))
            if target_item not in available:
                available[0] = target_item

        hours_since = []
        history_dict = {item: t for item, t in history}
        for item in available:
            if item in history_dict:
                hours = (target_time - history_dict[item]) / 6.0
                hours_since.append(hours)
            else:
                hours_since.append(-1.0)
                
        return {
            'item_seq': torch.tensor(item_seq, dtype=torch.long),
            'target_item': torch.tensor(target_item, dtype=torch.long),
            'available': torch.tensor(available, dtype=torch.long),
            'hours_since': torch.tensor(hours_since, dtype=torch.float),
            'target_time': torch.tensor(target_time, dtype=torch.long)
        }

def collate_eval_fn(batch):
    item_seq = torch.stack([x['item_seq'] for x in batch])
    target_item = torch.stack([x['target_item'] for x in batch])
    
    max_avail = max([len(x['available']) for x in batch])
    
    batch_available = []
    batch_hours = []
    
    for x in batch:
        avail = x['available']
        hours = x['hours_since']
        pad_len = max_avail - len(avail)
        if pad_len > 0:
            avail = torch.cat([avail, torch.zeros(pad_len, dtype=torch.long)])
            hours = torch.cat([hours, torch.full((pad_len,), -1.0, dtype=torch.float)])
        batch_available.append(avail)
        batch_hours.append(hours)
        
    return {
        'item_seq': item_seq,
        'target_item': target_item,
        'available': torch.stack(batch_available),
        'hours_since': torch.stack(batch_hours)
    }

def update_loss_curves(all_losses, ckpt_dir):
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        for name, losses in all_losses.items():
            if len(losses) > 0:
                plt.plot(range(1, len(losses)+1), losses, label=name, marker='o')
        plt.xlabel('Epoch')
        plt.ylabel('Average Training Loss')
        plt.title('Training Loss Curves')
        plt.legend()
        plt.grid(True)
        # overwrite existing file
        plt.savefig(ckpt_dir / 'loss_curves.png')
        plt.close()
    except Exception as e:
        print(f"\nCould not plot loss curves: {e}")

def train_and_evaluate(variant_name, use_repeat, use_availability, args, all_losses):
    print(f"\n--- Training Variant: {variant_name} ---")
    
    data_dir = Path(args.data_dir)
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    
    with open(data_dir / 'sequences.pkl', 'rb') as f:
        sequences = pickle.load(f)
    with open(data_dir / 'availability.pkl', 'rb') as f:
        availability = pickle.load(f)
    with open(data_dir / 'metadata.json', 'r') as f:
        metadata = json.load(f)
        
    n_items = metadata['num_items']
    
    train_seqs = {}
    test_samples = []
    
    user_subset = list(sequences.keys())
    
    for u in user_subset:
        seq = sequences[u]
        if len(seq) >= 3:
            train_seqs[u] = seq[:-1] 
            
            history = seq[:-1]
            target_item, target_time = seq[-1]
            test_samples.append((u, history, target_item, target_time))
            
    train_dataset = LiveRecDataset(train_seqs, availability)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn, num_workers=0)
    
    # Using fixed seed for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    
    model = LiveRec(n_items=n_items, hidden_dim=64, use_repeat=use_repeat, use_availability=use_availability)
    model = model.to(device)
    
    if torch.cuda.device_count() > 1:
        print(f"Wrapping model in DataParallel (Using {torch.cuda.device_count()} GPUs)")
        model = nn.DataParallel(model)
        
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    all_losses[variant_name] = []
    
    start_epoch = 0
    variant_safe_name = variant_name.replace(' ', '_').replace('+', 'plus').replace('(', '').replace(')', '').replace(',', '')
    
    # Check for existing checkpoint
    import glob
    ckpt_pattern = str(ckpt_dir / f"{variant_safe_name}_epoch*.pt")
    ckpt_files = glob.glob(ckpt_pattern)
    if ckpt_files:
        epochs = []
        for f in ckpt_files:
            try:
                ep = int(f.split('_epoch')[-1].split('.pt')[0])
                epochs.append((ep, f))
            except:
                pass
        if epochs:
            epochs.sort(key=lambda x: x[0])
            latest_ep, latest_file = epochs[-1]
            print(f"Resuming from checkpoint: {latest_file} at Epoch {latest_ep}")
            
            checkpoint = torch.load(latest_file, map_location=device)
            if isinstance(model, nn.DataParallel):
                model.module.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            start_epoch = latest_ep
            
            # Load previous losses if they exist to keep the graph continuous
            if 'loss' in checkpoint:
                # We can't recover the full history easily from just the last checkpoint 
                # unless we load all, but for now we just start tracking new ones.
                pass
    
    final_h1, final_h10, final_ndcg10 = 0.0, 0.0, 0.0
    
    test_dataset = EvalDataset(test_samples, availability)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size * 2, shuffle=False, collate_fn=collate_eval_fn, num_workers=0)
    
    for epoch in range(start_epoch, args.epochs):
        model.train()
        total_loss = 0
        progress = tqdm(train_loader, desc=f"Epoch {epoch+1}/{args.epochs}")
        for batch in progress:
            optimizer.zero_grad()
            
            item_seq = batch['item_seq'].to(device)
            target_item = batch['target_item'].to(device)
            neg_item = batch['neg_item'].to(device)
            available_ids = batch['available'].to(device)
            hours_since = batch['hours_since'].to(device) if use_repeat else None
            
            scores, top_ids, top_idx = model(item_seq, available_ids, hours_since, pos_id=target_item, neg_id=neg_item)
            
            pos_mask = (top_ids == target_item.unsqueeze(1))
            neg_mask = (top_ids == neg_item.unsqueeze(1)) & (top_ids != 0)
            
            pos_scores = (scores * pos_mask).sum(dim=1)
            neg_scores = (scores * neg_mask).sum(dim=1)
            
            valid_mask = (pos_mask.sum(dim=1) > 0) & (neg_mask.sum(dim=1) > 0)
            if valid_mask.sum() > 0:
                loss = -torch.nn.functional.logsigmoid(pos_scores[valid_mask] - neg_scores[valid_mask]).mean()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                progress.set_postfix({'loss': loss.item()})
        
        epoch_loss = total_loss / len(train_loader)
        all_losses[variant_name].append(epoch_loss)
        
        # Save checkpoint after every epoch
        variant_safe_name = variant_name.replace(' ', '_').replace('+', 'plus').replace('(', '').replace(')', '').replace(',', '')
        ckpt_path = ckpt_dir / f"{variant_safe_name}_epoch{epoch+1}.pt"
        
        torch.save({
            'epoch': epoch + 1,
            'variant_name': variant_name,
            'model_state_dict': model.module.state_dict() if isinstance(model, nn.DataParallel) else model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': epoch_loss,
        }, ckpt_path)
        
        # Plot curves incrementally at the end of each epoch
        update_loss_curves(all_losses, ckpt_dir)
            
        # -------------------------------------------------------------
        # Evaluate after every epoch
        # -------------------------------------------------------------
        model.eval()
        hit1, hit10, ndcg10 = 0.0, 0.0, 0.0
        count = 0
        
        eval_log_path = ckpt_dir / "eval_timing.txt"
        eval_start_time = __import__('time').time()
        
        with torch.no_grad():
            for batch_idx, batch in enumerate(tqdm(test_loader, desc=f"Evaluating Epoch {epoch+1}", mininterval=5.0)):
                item_seq = batch['item_seq'].to(device)
                available = batch['available'].to(device)
                hours_since = batch['hours_since'].to(device) if use_repeat else None
                target_tensor = batch['target_item'].to(device)
                
                scores, top_ids, _ = model(item_seq, available, hours_since)
                
                # Mask out padded positions (item ID 0) from being considered valid candidates
                pad_mask = (top_ids == 0)
                scores = scores.masked_fill(pad_mask, -float('inf'))
                
                h1 = hit_at_k(scores, top_ids, target_tensor, k=1).sum().item()
                h10 = hit_at_k(scores, top_ids, target_tensor, k=10).sum().item()
                n10 = ndcg_at_k(scores, top_ids, target_tensor, k=10).sum().item()
                
                hit1 += h1
                hit10 += h10
                ndcg10 += n10
                count += len(item_seq)
                
                if (batch_idx + 1) % (5000 // (args.batch_size * 2)) == 0:
                    elapsed = __import__('time').time() - eval_start_time
                    with open(eval_log_path, "a") as f_log:
                        f_log.write(f"Epoch {epoch+1} - Processed {count}/{len(test_samples)} eval examples. Elapsed: {elapsed:.2f}s\n")
                        
        final_h1 = hit1/count
        final_h10 = hit10/count
        final_ndcg10 = ndcg10/count
        
        # Save incremental results immediately
        results_csv = ckpt_dir / "results.csv"
        write_header = not results_csv.exists()
        with open(results_csv, 'a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['Variant', 'Epoch', 'Hit@1', 'Hit@10', 'NDCG@10'])
            writer.writerow([variant_name, epoch+1, final_h1, final_h10, final_ndcg10])
            
    return final_h1, final_h10, final_ndcg10

def main():
    parser = argparse.ArgumentParser(description="Train LiveRec sequential models")
    parser.add_argument("--data-dir", type=str, default="data/processed", help="Directory containing sequences.pkl, availability.pkl, metadata.json")
    parser.add_argument("--checkpoint-dir", type=str, default="backend/app/ml/checkpoints", help="Directory to save checkpoints and results")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs per variant")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size for training")
    parser.add_argument("--variants", type=str, default="all", choices=["all", "sasrec", "sasrec_avail", "sasrec_repeat", "liverec"], help="Which ablation variants to run")
    
    args = parser.parse_args()
    
    all_variants = {
        "sasrec": ("SASRec (No Avail, No Repeat)", False, False),
        "sasrec_avail": ("SASRec + Avail", False, True),
        "sasrec_repeat": ("SASRec + Repeat", True, False),
        "liverec": ("LiveRec (Avail + Repeat)", True, True)
    }
    
    if args.variants == "all":
        variants_to_run = list(all_variants.values())
    else:
        variants_to_run = [all_variants[args.variants]]
        
    print(f"Device: {device}")
    
    all_losses = {}
    results = []
    
    for name, use_rep, use_avail in variants_to_run:
        h1, h10, n10 = train_and_evaluate(name, use_rep, use_avail, args, all_losses)
        results.append((name, h1, h10, n10))
        
    print("\n\n--- Final Results ---")
    print(f"{'Variant':<35} | {'Hit@1':<8} | {'Hit@10':<8} | {'NDCG@10':<8}")
    print("-" * 65)
    for name, h1, h10, n10 in results:
        print(f"{name:<35} | {h1:.4f}   | {h10:.4f}   | {n10:.4f}")

if __name__ == "__main__":
    main()
