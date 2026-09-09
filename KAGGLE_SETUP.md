# SmartCast - Kaggle Training Setup Guide

This runbook provides the exact steps needed to train the LiveRec recommender end-to-end on a Kaggle multi-GPU Notebook.

## 1. Dataset Preparation

We do not need to re-run data preprocessing on Kaggle. We will upload the already-processed artifacts.

1. In Kaggle, go to **Datasets** -> **New Dataset**.
2. Name it something like `smartcast-processed-data`.
3. Upload the contents of your local `data/processed/` folder:
   - `sequences.pkl`
   - `availability.pkl`
   - `metadata.json`
4. Click **Create** and wait for the upload to finish.
5. In your Kaggle Notebook, click **Add Input** on the right sidebar and select your newly created dataset.

## 2. Notebook Execution

Open a new Kaggle Notebook, set the **Accelerator** to **GPU T4 x2** (or P100), and run the following commands in sequential cells.

### Cell 1: Clone Repository & Install Dependencies
```bash
!git clone https://github.com/YOUR_USERNAME/SmartCast.git
%cd SmartCast
!pip install -r requirements-kaggle.txt
```

### Cell 2: Validate GPU Environment
Make sure the environment can see your GPUs and perform tensor transfers before running a 2-hour job.
```bash
!python scripts/check_env.py
```

### Cell 3: Start Training
Execute the training script. We will override the data directory to point to the mounted dataset and the checkpoint directory to point to `/kaggle/working` so the files are easily accessible.

*(Note: Replace `smartcast-processed-data` in the path below if you named your dataset something else).*

```bash
!python backend/app/ml/train.py \
    --data-dir /kaggle/input/smartcast-processed-data \
    --checkpoint-dir /kaggle/working/checkpoints \
    --epochs 3 \
    --batch-size 128 \
    --variants all
```

## 3. Retrieving Results

Kaggle automatically wipes the `/kaggle/working/` directory at the end of interactive sessions if they disconnect. However, because our script saves checkpoints and results incrementally after *every* epoch, you can safely download partial progress while the script is running, or immediately after it finishes.

Your files will be located at:
- **Loss Curves:** `/kaggle/working/checkpoints/loss_curves.png`
- **Evaluation Metrics:** `/kaggle/working/checkpoints/results.csv`
- **Model Weights:** `/kaggle/working/checkpoints/*_epochN.pt`

**To download:**
Expand the **Output** section in the right sidebar (under `/kaggle/working`), open the `checkpoints` folder, click the **three dots** next to any file you want, and click **Download**.
