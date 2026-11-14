import pandas as pd
import numpy as np
from pathlib import Path
import time

print("Running Reconciliation Engine on 500,000+ rows...")
start_time = time.time()

data_dir = Path("csv data")

# ==========================================
# 1. LOAD THE MASSIVE DATASETS
# ==========================================
print("Loading raw files 1, 2, and 3...")
df_internal = pd.read_csv(data_dir / "1_internal_platform_logs.csv")
df_bank_1_to_1 = pd.read_csv(data_dir / "2_bank_settlement_1_to_1.csv")
df_bank_batch = pd.read_csv(data_dir / "3_bank_settlement_batch.csv")

# ==========================================
# 2. PHASE 1: EXACT 1:1 MATCHING
# ==========================================
print("Executing Phase 1: Line-by-Line Matching...")
recon_p1 = pd.merge(
    df_internal,
    df_bank_1_to_1,
    left_on='Txn_ID',
    right_on='Bank_Ref',
    how='left'
)

conditions_p1 = [
    (recon_p1['Bank_Ref'].notna()) & (recon_p1['Internal_Amount'] == recon_p1['Bank_Amount']),
    (recon_p1['Bank_Ref'].notna()) & (recon_p1['Internal_Amount'] != recon_p1['Bank_Amount'])
]
choices_p1 = ['MATCHED_EXACT', 'EXCEPTION_AMOUNT_MISMATCH']
recon_p1['Recon_Status'] = np.select(conditions_p1, choices_p1, default=recon_p1['Recon_Status'])

df_unmatched_p1 = recon_p1[recon_p1['Recon_Status'] == 'PENDING'].copy()

# ==========================================
# 3. PHASE 2: BATCH (MANY-TO-1) MATCHING
# ==========================================
print("Executing Phase 2: Batch Matching...")
internal_batch_summary = df_unmatched_p1.groupby('Batch_ID')['Internal_Amount'].sum().reset_index()
internal_batch_summary.rename(columns={'Internal_Amount': 'Total_Internal_Batch'}, inplace=True)

recon_p2 = pd.merge(
    internal_batch_summary,
    df_bank_batch,
    left_on='Batch_ID',
    right_on='Bank_Batch_ID',
    how='left'
)

conditions_p2 = [
    (recon_p2['Bank_Batch_ID'].notna()) & (recon_p2['Total_Internal_Batch'] == recon_p2['Settled_Amount']),
    (recon_p2['Bank_Batch_ID'].notna()) & (recon_p2['Total_Internal_Batch'] != recon_p2['Settled_Amount'])
]
choices_p2 = ['MATCHED_BATCH', 'EXCEPTION_BATCH_SHORTFALL']
recon_p2['Batch_Status'] = np.select(conditions_p2, choices_p2, default='MISSING_BANK_CREDIT')

# ==========================================
# 4. EXPORT FINAL POWER BI FILES
# ==========================================
print("Exporting updated files 4 and 5...")
recon_p1.to_csv(data_dir / "4_recon_phase1_exact_matches.csv", index=False)
recon_p2.to_csv(data_dir / "5_recon_phase2_batch_matches.csv", index=False)

end_time = time.time()
print(f"Engine finished in {round(end_time - start_time, 2)} seconds. Files 4 and 5 are now ready for Power BI.")