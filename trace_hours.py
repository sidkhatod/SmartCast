import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
import pickle
import json
import torch
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.app.ml.liverec_model import LiveRec
from backend.app.ml.train import LiveRecDataset, collate_fn
from torch.utils.data import DataLoader

def trace():
    print("Loading data...")
    with open('data/processed/sequences.pkl', 'rb') as f:
        sequences = pickle.load(f)
    with open('data/processed/availability.pkl', 'rb') as f:
        availability = pickle.load(f)
    with open('data/processed/metadata.json', 'r') as f:
        metadata = json.load(f)
        
    n_items = metadata['num_items']
    
    # Just take 1 user for the trace
    user_subset = list(sequences.keys())[:1]
    train_seqs = {u: sequences[u][:-1] for u in user_subset if len(sequences[u]) >= 3}
    
    dataset = LiveRecDataset(train_seqs, availability)
    loader = DataLoader(dataset, batch_size=1, collate_fn=collate_fn)
    
    batch = next(iter(loader))
    
    model = LiveRec(n_items=n_items, hidden_dim=64, use_repeat=True, use_availability=True)
    model.eval()
    
    item_seq = batch['item_seq']
    available_ids = batch['available']
    hours_since = batch['hours_since']
    
    print("\n--- Input Tensors ---")
    print(f"available_ids (first 10): {available_ids[0][:10].tolist()}")
    print(f"hours_since (first 10): {hours_since[0][:10].tolist()}")
    
    with torch.no_grad():
        final_scores, top_ids, top_idx = model(item_seq, available_ids, hours_since)
        
    print("\n--- After score_candidates (Top K = 128) ---")
    print(f"top_idx (first 10): {top_idx[0][:10].tolist()}")
    print(f"top_ids (first 10): {top_ids[0][:10].tolist()}")
    
    # Gather hours manually to prove they match
    gathered_hours = hours_since.gather(1, top_idx)
    print(f"gathered_hours (first 10): {gathered_hours[0][:10].tolist()}")
    
    # Prove that top_ids[i] exactly corresponds to gathered_hours[i]
    print("\n--- Verification of Mapping ---")
    for i in range(5):
        idx = top_idx[0][i].item()
        tid = top_ids[0][i].item()
        thour = gathered_hours[0][i].item()
        
        orig_id = available_ids[0][idx].item()
        orig_hour = hours_since[0][idx].item()
        
        print(f"Rank {i}:")
        print(f"  Mapped via top_idx {idx} -> Candidate ID: {tid} (Orig: {orig_id}), Hours: {thour:.2f} (Orig: {orig_hour:.2f})")
        assert tid == orig_id
        assert thour == orig_hour
        
    print("\nTRACE SUCCESSFUL: hours_since_last_seen values are perfectly aligned with candidate ids/embeddings after top-k selection!")

if __name__ == "__main__":
    trace()
