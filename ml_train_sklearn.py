#!/usr/bin/env python3
"""
Alpha158 模型训练与回测 - 使用sklearn
"""
import sys
sys.path.insert(0, '/Users/wangqingxiang/.openclaw/workspace')

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# 文件路径
TRAIN_FILE = '/Users/wangqingxiang/.openclaw/workspace/ml_dataset_train.csv'
TEST_FILE = '/Users/wangqingxiang/.openclaw/workspace/ml_dataset_test.csv'

LABEL_MAP = {-1: '下跌', 0: '震荡', 1: '上涨'}

def load_data():
    """加载数据"""
    print("\n" + "="*80)
    print("📊 加载数据")
    print("="*80)
    
    df_train = pd.read_csv(TRAIN_FILE)
    df_test = pd.read_csv(TEST_FILE)
    
    print(f"   训练集: {len(df_train)} 样本")
    print(f"   测试集: {len(df_test)} 样本")
    
    feature_cols = [c for c in df_train.columns if c not in ['ticker','date','price','future_return_20d','label','dataset']]
    
    X_train = df_train[feature_cols].copy().fillna(0).replace([np.inf, -np.inf], 0)
    y_train = df_train['label'].copy()
    X_test = df_test[feature_cols].copy().fillna(0).replace([np.inf, -np.inf], 0)
    y_test = df_test['label'].copy()
    
    print(f"   特征数: {len(feature_cols)}")
    print(f"   训练集标签: {dict(y_train.value_counts())}")
    print(f"   测试集标签: {dict(y_test.value_counts())}")
    
    return X_train, y_train, X_test, y_test, feature_cols, df_test

def train_models(X_train, y_train):
    """训练多个模型"""
    print("\n" + "="*80)
    print("🤖 训练模型")
    print("="*80)
    
    models = {}
    
    # RandomForest
    print("\n1. Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    models['RandomForest'] = rf
    print("   ✓ 完成")
    
    # GradientBoosting
    print("\n2. Gradient Boosting...")
    gb = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
    gb.fit(X_train, y_train)
    models['GradientBoosting'] = gb
    print("   ✓ 完成")
    
    return models

def evaluate_model(name, model, X_test, y_test):
    """评估模型"""
    print(f"\n" + "="*80)
    print(f"📈 {name} 评估")
    print("="*80)
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"\n🎯 整体指标:")
    print(f"   准确率: {acc:.4f} ({acc*100:.2f}%)")
    print(f"   F1分数: {f1:.4f}")
    
    print(f"\n📋 分类报告:")
    print(classification_report(y_test, y_pred, target_names=['下跌', '震荡', '上涨']))
    
    print(f"\n🔢 混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"        预测下跌  预测震荡  预测上涨")
    for i, row in enumerate(cm):
        actual = ['下跌', '震荡', '上涨'][i]
        print(f"实际{actual}:  {row[0]:5d}     {row[1]:5d}     {row[2]:5d}")
    
    return y_pred, y_pred_proba, acc, f1

def feature_importance(model, feature_cols, name):
    """特征重要性"""
    print(f"\n" + "="*80)
    print(f"🔑 {name} - Top 20 重要因子")
    print("="*80)
    
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
        feat_imp = pd.DataFrame({
            'feature': feature_cols,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        print("\n排名  因子名称              重要性")
        print("-"*50)
        for i, (_, row) in enumerate(feat_imp.head(20).iterrows()):
            print(f"{i+1:2d}.   {row['feature']:20s} {row['importance']:.4f}")
        
        return feat_imp
    return None

def backtest_analysis(y_true, y_pred, y_pred_proba, df_test):
    """回测分析"""
    print("\n" + "="*80)
    print("📊 回测分析")
    print("="*80)
    
    df = df_test.copy()
    df['actual'] = y_true
    df['pred'] = y_pred
    df['confidence'] = np.max(y_pred_proba, axis=1)
    
    # 置信度分层
    high_conf = df[df['confidence'] > 0.5]
    med_conf = df[(df['confidence'] > 0.4) & (df['confidence'] <= 0.5)]
    
    print(f"\n按置信度分析:")
    
    for name, subset in [("高置信度 (>50%)", high_conf), ("中等置信度 (40-50%)", med_conf)]:
        if len(subset) > 0:
            acc = (subset['actual'] == subset['pred']).sum() / len(subset)
            print(f"\n{name}:")
            print(f"   样本数: {len(subset)}")
            print(f"   准确率: {acc:.4f} ({acc*100:.1f}%)")
            
            # 各标签准确率
            for label in [-1, 0, 1]:
                label_data = subset[subset['actual'] == label]
                if len(label_data) > 0:
                    label_acc = (label_data['actual'] == label_data['pred']).sum() / len(label_data)
                    print(f"   {LABEL_MAP[label]}识别率: {label_acc:.2f}")
    
    return df

def trading_signals(df_test, y_pred, y_pred_proba):
    """生成交易信号"""
    print("\n" + "="*80)
    print("💰 交易信号")
    print("="*80)
    
    df = df_test.copy()
    df['signal'] = y_pred
    df['confidence'] = np.max(y_pred_proba, axis=1)
    df['signal_name'] = df['signal'].map(LABEL_MAP)
    df['correct'] = (df['label'] == df['signal']).astype(int)
    
    # 只看高置信度信号
    signals = df[df['confidence'] > 0.45].sort_values('date')
    
    print(f"\n高置信度信号 (>45%):")
    print("-"*70)
    print(f"{'日期':<12} {'股票':<8} {'信号':<6} {'置信度':<8} {'实际':<6} {'正确':<6}")
    print("-"*70)
    
    for _, row in signals.iterrows():
        print(f"{row['date']:<12} {row['ticker']:<8} {row['signal_name']:<6} {row['confidence']:.2%}     {LABEL_MAP[row['label']]:<6} {'✓' if row['correct'] else '✗'}")
    
    if len(signals) > 0:
        total = len(signals)
        correct = signals['correct'].sum()
        print("-"*70)
        print(f"总计: {total}信号, 正确{correct}, 胜率{correct/total*100:.1f}%")
    
    return signals

def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 Alpha158 模型训练与回测 (sklearn)")
    print("="*80)
    
    # 加载数据
    X_train, y_train, X_test, y_test, feature_cols, df_test = load_data()
    
    # 训练
    models = train_models(X_train, y_train)
    
    results = {}
    for name, model in models.items():
        print("\n")
        y_pred, y_pred_proba, acc, f1 = evaluate_model(name, model, X_test, y_test)
        feat_imp = feature_importance(model, feature_cols, name)
        
        results[name] = {
            'model': model,
            'pred': y_pred,
            'proba': y_pred_proba,
            'acc': acc,
            'f1': f1,
            'feature_importance': feat_imp
        }
    
    # 选择最佳模型
    best_name = max(results.keys(), key=lambda x: results[x]['acc'])
    print("\n" + "="*80)
    print(f"🏆 最佳模型: {best_name} (准确率: {results[best_name]['acc']:.2%})")
    print("="*80)
    
    # 回测
    best_result = results[best_name]
    df = backtest_analysis(y_test, best_result['pred'], best_result['proba'], df_test)
    
    # 交易信号
    signals = trading_signals(df_test, best_result['pred'], best_result['proba'])
    
    # 保存
    df.to_csv('/Users/wangqingxiang/.openclaw/workspace/ml_predictions.csv', index=False)
    
    print("\n" + "="*80)
    print("✅ 完成!")
    print("="*80)
    print(f"\n💾 结果保存: ml_predictions.csv")
    
    return results

if __name__ == "__main__":
    results = main()
