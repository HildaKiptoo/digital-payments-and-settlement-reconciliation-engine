import pandas as pd
import numpy as np
from pathlib import Path
import time

print("Generating 500,000+ transactions. Please wait...")
start_time = time.time()

# ==========================================
# 1. PARAMETERS & VECTORIZED GENERATION
# ==========================================
N_ROWS = 500000
BATCH_SIZE = 50  # Average transactions per batch

# Generate core internal transaction log
np.random.seed(42) # For reproducibility
txn_ids = [f'TXN{str(i).zfill(7)}' for i in range(1, N_ROWS + 1)]

# Create batches (roughly 50 transactions per batch)
batch_ids = [f'B-{str(i).zfill(5)}' for i in np.repeat(range(1, (N_ROWS // BATCH_SIZE) + 2), BATCH_SIZE)[:N_ROWS]]

# Generate random transaction amounts in KES (between 50 and 15,000)
amounts = np.round(np.random.uniform(50.0, 15000.0, N_ROWS), 2)

# Create the Internal Data DataFrame
df_internal = pd.DataFrame({
    'Txn_ID': txn_ids,
    'Batch_ID': batch_ids,
    'Internal_Amount': amounts,
    'Recon_Status': 'PENDING'
})

# ==========================================
# 2. SPLITTING INTO 1:1 AND BATCH PROCESSING
# ==========================================
# Simulate that 60% of transactions are processed 1:1, and 40% are batched
mask_1_to_1 = np.random.rand(N_ROWS) < 0.60
df_internal_1_to_1 = df_internal[mask_1_to_1].copy()
df_internal_batch = df_internal[~mask_1_to_1].copy()

# ==========================================
# 3. BANK FILE 1 (LINE-BY-LINE) WITH EXCEPTIONS
# ==========================================
df_bank_1_to_1 = df_internal_1_to_1[['Txn_ID', 'Internal_Amount']].copy()
df_bank_1_to_1.rename(columns={'Txn_ID': 'Bank_Ref', 'Internal_Amount': 'Bank_Amount'}, inplace=True)

# Inject Exceptions (Value at Risk):
# 1. Missing Bank Credits (Drop 2% of the transactions)
drop_indices = df_bank_1_to_1.sample(frac=0.02, random_state=1).index
df_bank_1_to_1 = df_bank_1_to_1.drop(drop_indices)

# 2. Amount Mismatches (Alter amounts by +/- 50 KES for 3% of transactions to simulate hidden gateway fees)
mismatch_indices = df_bank_1_to_1.sample(frac=0.03, random_state=2).index
df_bank_1_to_1.loc[mismatch_indices, 'Bank_Amount'] -= 50.0

# ==========================================
# 4. BANK FILE 2 (BATCH SETTLEMENTS) WITH EXCEPTIONS
# ==========================================
# Group the 40% batched transactions
df_bank_batch = df_internal_batch.groupby('Batch_ID')['Internal_Amount'].sum().reset_index()
df_bank_batch.rename(columns={'Batch_ID': 'Bank_Batch_ID', 'Internal_Amount': 'Settled_Amount'}, inplace=True)

# Inject Exceptions (Batch Shortfalls):
# Reduce the settled amount by random percentages (1% to 5%) for 5% of the batches
shortfall_indices = df_bank_batch.sample(frac=0.05, random_state=3).index
df_bank_batch.loc[shortfall_indices, 'Settled_Amount'] = np.round(
    df_bank_batch.loc[shortfall_indices, 'Settled_Amount'] * np.random.uniform(0.95, 0.99, len(shortfall_indices)), 2
)

# ==========================================
# 5. EXPORT THE MASSIVE DATASETS
# ==========================================
output_dir = Path("csv data")
output_dir.mkdir(parents=True, exist_ok=True)

df_internal.to_csv(output_dir / "1_internal_platform_logs.csv", index=False)
df_bank_1_to_1.to_csv(output_dir / "2_bank_settlement_1_to_1.csv", index=False)
df_bank_batch.to_csv(output_dir / "3_bank_settlement_batch.csv", index=False)

end_time = time.time()
print(f"Successfully generated {len(df_internal):,} internal transactions.")
print(f"Exported to '{output_dir.resolve()}' in {round(end_time - start_time, 2)} seconds.")