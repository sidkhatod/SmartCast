# ML Integration Report

## Phase 0: Fix before building anything else
- **Status:** Completed
- **Changes:** Updated `causal_mask` in `backend/app/ml/liverec_model.py`'s `SequenceEncoder` from a float tensor with `-inf` to a boolean tensor using `torch.ones` with `dtype=torch.bool`.
- **Verification:** Ran a throwaway forward pass with a dummy tensor. The PyTorch deprecation/mismatched-mask-dtype warning is resolved and the model executes correctly.

## Phase 1: Environment
- **Status:** Completed
- **Virtual Environment:** Created 'smartcast' venv. Activation command: .\smartcast\Scripts\Activate.ps1`n- **Installed Packages:** pandas==3.0.5, numpy==2.5.3, torch==2.14.0+cpu, scikit-learn==1.9.0, tqdm==4.70.0. Added to new requirements-ml.txt.


## Phase 2: Alembic Baseline
- **Status:** Completed
- **Steps Taken:** Ran \lembic init alembic\, configured \env.py\ to import \Base\ and all models (\user, stream, analytics, chat\), and pointed to \settings.DATABASE_URL\. Fixed an existing bug in \chat.py\ (missing \Float\ import, reserved \metadata\ column name).
- **Verification:** Since the local Docker Postgres container was unavailable, temporarily pointed Alembic to a local SQLite DB. Generated the baseline migration covering the current schema and confirmed \lembic upgrade head\ applies it cleanly. Restored \DATABASE_URL\ to Postgres for future use.


## Phase 3: Data Preprocessing
- **Status:** In Progress
- **Steps Taken:** Wrote \data/preprocess.py\. It reads \100k_a.csv\ (3+ million rows), remaps user and item IDs (reserving 0 for padding), builds the availability index by tracking the min start and max stop time for each stream, builds user viewing sequences, filters users with < 3 interactions, and saves artifacts (\sequences.pkl\, \vailability.pkl\, etc.) to \data/processed/\.
- **Current State:** Script is running in the background and populating the availability index.

- **Result:** Processed 3.05M interactions into 100k valid user sequences. Saved to \data/processed/\.


## Phase 4: Training & Evaluation
- **Status:** In Progress
- **Steps Taken:** Wrote \ackend/app/ml/train.py\ implementing a PyTorch \Dataset\ with 10-minute timestep padding and LiveRec-specific dynamic candidate subsetting (simulating a live availability index). Training loops over 4 model variants (SASRec, SASRec+Avail, SASRec+Repeat, LiveRec). Had to troubleshoot and fix a PyTorch DLL loading issue on Windows by downgrading Torch to \2.4.1+cpu\ and forcing \KMP_DUPLICATE_LIB_OK=True\.\n- **Current State:** The models are actively training and evaluating on the preprocessed 100k data slice.


- **Results (500 users, 1 epoch):**
| Variant | Hit@1 | Hit@10 | NDCG@10 |
| --- | --- | --- | --- |
| SASRec (No Avail, No Repeat) | 0.0040 | 0.0380 | 0.0168 |
| SASRec + Avail | 0.0100 | 0.0500 | 0.0251 |
| SASRec + Repeat | 0.0060 | 0.0540 | 0.0254 |
| LiveRec (Avail + Repeat) | 0.0020 | 0.0320 | 0.0131 |

**Note**: The model ran for only 1 epoch on a small subset of 500 users to establish system integration and correct inference dynamics without timing out the session.

