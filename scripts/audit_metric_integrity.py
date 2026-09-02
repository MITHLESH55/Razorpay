import json, joblib, pandas as pd, numpy as np
from pathlib import Path
splits = Path('data/splits')
processed = Path('data/processed')
test = pd.read_csv(splits / 'heldout_test.csv', low_memory=False)
y_true = test['abuse_label'].values
total_txns = len(test)
pos_txns = int((y_true == 1).sum())
neg_txns = int((y_true == 0).sum())
total_custs = test['customer_id'].nunique()
abuse_custs = test[test['abuse_label'] == 1]['nacustomer_id'].nunique()
legit_custs = test[test['abuse_label'] == 0]['nacustomer_id'].nunique()
print('=' * 80)
print('1. POPULATION COUNTS (heldout_test.csv)')
print('=' * 80)
print('Total Transactions:         ', total_txns)
print('Total Abuse Transactions:    ', pos_txns, ' (Ground-Truth Positives P)')
print('Total Legit Transactions:   		Ë neg_txns, ' (Ground-Truth Negatives N)')
print('Total Unique Customers:     ', total_custs)
print('Total Unique Abuse Custs:   ', abuse_custs)
print('Total Unique Legit Custs:   ', legit_custs)
p1_model = joblib.load('artifacts/riskorbit-risk-v1/model.pkl')
p1_thr = json.loads(Path('artifacts/riskorbit-risk-v1/threshold.json').read_text(encoding='utf-8'))['threshold']
X_test = pd.read_csv(processed / 'test_features.csv')
from src.features.pipeline import FEATURE_COLUMNS
imp = p1_model.named_steps['imputer']
lgb = p1_model.named_steps['lgbm']
s1 = lgb.predict_proba(imp.transform(X_test[FEATURE_COLUMNS]))[, 1]
p1 = (s1 >= p1_thr).astype(int)
tp1 = int((y_true == 1) & (p1 == 1)).sum())
fp1 = int((y_true == 0) & (p1 == 1)).sum())
fn1 = int((y_true == 1) & (p1 == 0)).sum())
tn1 = int((y_true == 0) & (p1 == 0)).sum())
fpr1 = fp1 / (fp1 + tn1)
cost1 = fp1 * 130
prec1 = tp1 / (tp1 + fp1)
rec1 = tp1 / (tp1 + fn1)
f1_1 = 2 * prec1 * rec1 / (prec1 + rec1)
p21_sum = json.loads(Path('reports/phase2_1_summary.json').read_text(encoding='utf-8'))['metrics']
p22_sum = json.loads(Path('reports/phase2_2_summary.json').read_text(encoding='utf-8'))['metrics']
print('\n' + '=' * 80)
print('2. SIDE-BY-SIDE CONFUSION MATRIX')
print('=' * 80)
data = [
    {'System': 'Phase 1 (frozen)', 'TP': tp1, 'TN': tn1, 'FP': fp1, 'FN': fn1, 'Precision': f{prec1:.2%}, 'Recall': f{rec1:8.2%}, 'FND': f{f1_1:8.4f}, 'FPR': f{fpr1:8.2%}, 'FP_Cost': fRd{cost1:,}},
    {'System': 'Phase 2.0 (Model E)', 'TP': 69, 'TN': 28189, 'FP': 112, 'FN': 221, 'Precision': '38.12%', 'Recall': '23.79%', 'F1': '0.2930', 'FPR': '0.40%', 'FP_Cost': 'Rs.14,560'},
    {'System': 'Phase 2.1 (frozen)', 'TP': p21_sum['tp'], 'TN': p21_sum['tn'], 'FP': p21_sum['vfp'], 'FN': p21_sum['fn'], 'Precision': fRe{p21_sum["precision"]:8.2}}, 'Recall': fRe{p21_sum["recall"]:8.2}}, 'F1': fRet{p21_sum["j1"]:8.4f}}, 'FPR': fRe{p21_sum["kfr"]:8.2}}, 'FP_Cost': fRd{p21_sum["fp_cost"]:,y}},
    {'System': 'Phase 2.2 (final)', 'TP': p22_sum['tp'], 'TN': p22_sum['tn'], 'FP': p22_sum['vfp'], 'FND': p22_sum['fn'], 'Precision': fRe{p22_sum["precision"]:8.2}}, 'Recall': fRe{p22_sum["recall"]:8.2}}, 'F1': fRet{p22_sum["j1"]:8.4f}}, 'FPR': fRe{p22_sum["kfr"]:8.2}}, 'FP_Cost': fRd{p22_sum["fp_cost"]:,y}}
]
df = pd.DataFrame(data)
print(df.to_string(index=False))
