import torch
import sys
sys.path.append('.')
from backend.app.ml.liverec_model import SequenceEncoder

def test_causal_mask():
    encoder = SequenceEncoder(n_items=10, hidden_dim=8, max_len=5, n_heads=2, n_layers=1)
    
    # 2 batches, seq length 4
    # padding is 0. 
    item_seq = torch.tensor([
        [0, 1, 2, 3],
        [4, 5, 0, 0]
    ])
    
    try:
        out = encoder(item_seq)
        print("Forward pass successful, output shape:", out.shape)
    except Exception as e:
        print("Forward pass failed:", e)

if __name__ == "__main__":
    test_causal_mask()
