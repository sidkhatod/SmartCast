import os
import pickle
import json
import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np

import sys
sys.path.append("backend/app/ml")
from liverec_model import LiveRec, hit_at_k, ndcg_at_k
from train import EvalDataset, collate_eval_fn

def run_eval_test():
    print("Loading data...")
    data_dir = "data/processed"
    with open(f'{data_dir}/sequences.pkl', 'rb') as f:
        sequences = pickle.load(f)
    with open(f'{data_dir}/availability.pkl', 'rb') as f:
        availability = pickle.load(f)
    with open(f'{data_dir}/metadata.json', 'r') as f:
        metadata = json.load(f)
        
    n_items = metadata['num_items']
    
    test_samples = []
    
    # Restrict to 10000 users to match the 'comparable subset'
    user_subset = list(sequences.keys())[:10000]
    
    for u in user_subset:
        seq = sequences[u]
        if len(seq) >= 3:
            history = seq[:-1]
            target_item, target_time = seq[-1]
            test_samples.append((u, history, target_item, target_time))
            
    print(f"Total test samples: {len(test_samples)}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # We will test all 4 variants randomly initialized
    all_variants = {
        "sasrec": ("SASRec (No Avail, No Repeat)", False, False),
        "sasrec_avail": ("SASRec + Avail", False, True),
        "sasrec_repeat": ("SASRec + Repeat", True, False),
        "liverec": ("LiveRec (Avail + Repeat)", True, True)
    }
    
    test_dataset = EvalDataset(test_samples, availability)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False, collate_fn=collate_eval_fn, num_workers=0)
    
    results = []
    
    for var_key, (name, use_rep, use_avail) in all_variants.items():
        torch.manual_seed(42)
        np.random.seed(42)
        
        model = LiveRec(n_items=n_items, hidden_dim=64, use_repeat=use_rep, use_availability=use_avail).to(device)
        model.eval()
        
        hit1, hit10, ndcg10 = 0.0, 0.0, 0.0
        count = 0
        
        with torch.no_grad():
            for batch in test_loader:
                item_seq = batch['item_seq'].to(device)
                available = batch['available'].to(device)
                hours_since = batch['hours_since'].to(device) if use_rep else None
                target_tensor = batch['target_item'].to(device)
                
                scores, top_ids, _ = model(item_seq, available, hours_since)
                
                # Mask out padded positions
                pad_mask = (top_ids == 0)
                scores = scores.masked_fill(pad_mask, -float('inf'))
                
                h1 = hit_at_k(scores, top_ids, target_tensor, k=1).sum().item()
                h10 = hit_at_k(scores, top_ids, target_tensor, k=10).sum().item()
                n10 = ndcg_at_k(scores, top_ids, target_tensor, k=10).sum().item()
                
                hit1 += h1
                hit10 += h10
                ndcg10 += n10
                count += len(item_seq)
                
        final_h1 = hit1/count
        final_h10 = hit10/count
        final_ndcg10 = ndcg10/count
        results.append((name, final_h1, final_h10, final_ndcg10))
        
    print("\n\n--- Batched Eval Results (10k subset) ---")
    print(f"{'Variant':<35} | {'Hit@1':<8} | {'Hit@10':<8} | {'NDCG@10':<8}")
    print("-" * 65)
    for name, h1, h10, n10 in results:
        print(f"{name:<35} | {h1:.4f}   | {h10:.4f}   | {n10:.4f}")

if __name__ == "__main__":
    run_eval_test()
