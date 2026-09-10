import os
import pickle
import json
import torch
import torch.nn as nn
from tqdm import tqdm
import time
import numpy as np
import gc

import psutil

# Add ml folder to path
import sys
sys.path.append("backend/app/ml")
from liverec_model import LiveRec, hit_at_k, ndcg_at_k

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
    
    # We take all users up to a point
    user_subset = list(sequences.keys())
    
    for u in user_subset:
        seq = sequences[u]
        if len(seq) >= 3:
            history = seq[:-1]
            target_item, target_time = seq[-1]
            test_samples.append((u, history, target_item, target_time))
            
    print(f"Total test samples: {len(test_samples)}")
    
    # Take first 50,000 for the test to see degradation
    test_samples = test_samples[:50000]
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LiveRec(n_items=n_items, hidden_dim=64, use_repeat=True, use_availability=True).to(device)
    model.eval()
    
    print("Starting evaluation...")
    
    hit1, hit10, ndcg10 = 0.0, 0.0, 0.0
    count = 0
    
    use_repeat = True
    
    start_time = time.time()
    
    log_file = open("eval_speed_log.txt", "w")
    
    process = psutil.Process(os.getpid())
    
    with torch.no_grad():
        for u, history, target_item, target_time in test_samples:
            item_seq = [item for item, t in history]
            if len(item_seq) >= 50:
                item_seq = item_seq[-50:]
            else:
                item_seq = [0] * (50 - len(item_seq)) + item_seq
                
            item_seq = torch.tensor([item_seq], dtype=torch.long).to(device)
            
            available = list(availability.get(target_time, []))
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
                    
            available = torch.tensor([available], dtype=torch.long).to(device)
            hours_since = torch.tensor([hours_since], dtype=torch.float).to(device) if use_repeat else None
            
            target_tensor = torch.tensor([target_item], dtype=torch.long).to(device)
            
            scores, top_ids, _ = model(item_seq, available, hours_since)
            
            h1 = hit_at_k(scores, top_ids, target_tensor, k=1).item()
            h10 = hit_at_k(scores, top_ids, target_tensor, k=10).item()
            n10 = ndcg_at_k(scores, top_ids, target_tensor, k=10).item()
            
            hit1 += h1
            hit10 += h10
            ndcg10 += n10
            count += 1
            
            if count % 5000 == 0:
                elapsed = time.time() - start_time
                mem_mb = process.memory_info().rss / (1024 * 1024)
                gpu_mem = torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0
                msg = f"Processed {count} samples. Elapsed: {elapsed:.2f}s. Sys Mem: {mem_mb:.2f} MB. GPU Mem: {gpu_mem:.2f} MB\n"
                print(msg, end="")
                log_file.write(msg)
                log_file.flush()
                
    log_file.close()
    print("Done!")

if __name__ == "__main__":
    run_eval_test()
