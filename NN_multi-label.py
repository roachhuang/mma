import torch
import torch.nn as nn
import torch.optim as optim

# Define your neural network architecture
class StockPredictionModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(StockPredictionModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

# Example usage
input_size = 4  # Number of features (RSI, MACD, Bollinger Bands, SMV)
hidden_size = 16  # Adjust as needed
output_size = 3  # 3 classes: buy, sell, hold

model = StockPredictionModel(input_size, hidden_size, output_size)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Assuming you have your data (X_train, y_train) ready
for epoch in range(epochs):
    optimizer.zero_grad()
    outputs = model(X_train)
    loss = criterion(outputs, y_train)
    loss.backward()
    optimizer.step()

# To make predictions:
with torch.no_grad():
    test_outputs = model(X_test)
    predicted_labels = torch.argmax(test_outputs, dim=1)

# Now `predicted_labels` contains the predicted labels (0, 1, or 2) for your test data
