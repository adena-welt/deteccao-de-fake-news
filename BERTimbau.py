# -*- coding: utf-8 -*-
"""BERTimbau.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1HY4f12R-Mh46wIZ9tEbRKZFibhBl6p8Q
"""

import torch
from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, confusion_matrix
import pandas as pd

from google.colab import drive
drive.mount('/content/drive', force_remount=True)

# Carregar o arquivo CSV
# Caminho do dataset
dataset_dir = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQHXeGnay1fBg89k_lUubL_3WsML0F7lrjDTF96jMUGaFDXGjR9Y_ca7g8cjjG4XzHSZoJo7bFp1ZWF/pub?gid=1447023203&single=true&output=csv'
data = pd.read_csv(dataset_dir)

# Convertendo os rótulos para minúsculas
data['label'] = data['label'].str.lower()

# Mapeando os rótulos para valores numéricos
label_map = {'fake': 0, 'true': 1}
data['label'] = data['label'].map(label_map)

# Garantir que todas as notícias possuam tamanho 500
data['preprocessed_news'] = data['preprocessed_news'].apply(lambda x: x[:500].ljust(500))

# Dividir os dados em conjuntos de treino, validação e teste
train_data, test_data = train_test_split(data, test_size=0.2, random_state=42, stratify=data['label'])
train_data, val_data = train_test_split(train_data, test_size=0.2, random_state=42, stratify=train_data['label'])

# Imprimir o número de notícias em cada classe nos conjuntos de dados
num_train_fake = len(train_data[train_data['label'] == 0])
num_train_true = len(train_data[train_data['label'] == 1])
num_val_fake = len(val_data[val_data['label'] == 0])
num_val_true = len(val_data[val_data['label'] == 1])
num_test_fake = len(test_data[test_data['label'] == 0])
num_test_true = len(test_data[test_data['label'] == 1])

print("Número de notícias no conjunto de treino:")
print(f"Classe 'fake': {num_train_fake}")
print(f"Classe 'true': {num_train_true}")

print("\nNúmero de notícias no conjunto de validação:")
print(f"Classe 'fake': {num_val_fake}")
print(f"Classe 'true': {num_val_true}")

print("\nNúmero de notícias no conjunto de teste:")
print(f"Classe 'fake': {num_test_fake}")
print(f"Classe 'true': {num_test_true}")

#Definir o modelo BERTimbau e o tokenizer
model_name = 'neuralmind/bert-base-portuguese-cased'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)

class CustomDataset(Dataset):
    def __init__(self, data, tokenizer, max_length=256):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        text = self.data.iloc[idx]['preprocessed_news']
        label = self.data.iloc[idx]['label']  # Mantendo como string
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            truncation=True,
            return_token_type_ids=False,
            padding='max_length',
            return_attention_mask=True,
            return_tensors='pt'
        )
        input_ids = encoding['input_ids'].flatten()
        attention_mask = encoding['attention_mask'].flatten()
        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'label': torch.tensor(label, dtype=torch.long)
        }

# Criar os datasets e data loaders
train_dataset = CustomDataset(train_data, tokenizer)
val_dataset = CustomDataset(val_data, tokenizer)
test_dataset = CustomDataset(test_data, tokenizer)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

# Definir o dispositivo
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Treinar o modelo
model.to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
criterion = torch.nn.CrossEntropyLoss()

for epoch in range(5):
    model.train()
    for batch in train_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        loss.backward()
        optimizer.step()

    # Avaliar o modelo no conjunto de validação
    model.eval()
    val_preds = []
    val_labels = []
    for batch in val_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1)

        val_preds.extend(preds.cpu().numpy())
        val_labels.extend(labels.cpu().numpy())

    val_accuracy = accuracy_score(val_labels, val_preds)
    print(f'Epoch {epoch+1}, Validation Accuracy: {val_accuracy}')

    # Avaliar o modelo no conjunto de teste
    model.eval()
    test_preds = []
    test_labels = []
    for batch in test_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1)

        test_preds.extend(preds.cpu().numpy())
        test_labels.extend(labels.cpu().numpy())

    test_accuracy = accuracy_score(test_labels, test_preds)
    test_precision = precision_score(test_labels, test_preds)
    test_recall = recall_score(test_labels, test_preds)
    test_f1 = f1_score(test_labels, test_preds)
    print(f'Epoch {epoch+1}, Test Accuracy: {test_accuracy}, Precision: {test_precision}, Recall: {test_recall}, F1-score: {test_f1}')

# Calcular a matriz de confusão e outras métricas
conf_matrix = confusion_matrix(test_labels, test_preds)
test_accuracy = accuracy_score(test_labels, test_preds)
test_precision = precision_score(test_labels, test_preds)
test_recall = recall_score(test_labels, test_preds)
test_f1 = f1_score(test_labels, test_preds)

# Imprimir a matriz de confusão e outras métricas
print("Confusion Matrix:")
print(conf_matrix)
print(f'Test Accuracy: {test_accuracy}, Precision: {test_precision}, Recall: {test_recall}, F1-score: {test_f1}')

import os
from google.colab import files

# Salvar o modelo localmente
model_save_path = 'bertimbau_model.pth'
torch.save(model.state_dict(), model_save_path)

# Baixar o arquivo do modelo
from google.colab import files
files.download(model_save_path)

# Salvar o tokenizador localmente
tokenizer_save_path = 'modelos_bertimbau/'
tokenizer.save_pretrained(tokenizer_save_path)

# Compactar a pasta do tokenizador
import shutil
shutil.make_archive('modelos_bertimbau', 'zip', tokenizer_save_path)

# Baixar o arquivo compactado
files.download('modelos_bertimbau.zip')