import torch
import torch.nn as nn
import torch.nn.functional as F

class AttentionLayer(nn.Module):
    """
    Attention mechanism to weight the importance of time steps and channels.
    """
    def __init__(self, hidden_size, num_channels):
        super(AttentionLayer, self).__init__()
        self.attn = nn.Linear(hidden_size, 1)
        self.num_channels = num_channels

    def forward(self, x):
        # x shape: (batch_size, num_channels, seq_len, hidden_size)
        # Compute attention scores for each time step
        batch_size, num_channels, seq_len, hidden_size = x.size()
        attn_weights = torch.tanh(self.attn(x))  # shape: (batch_size, num_channels, seq_len, 1)
        attn_weights = F.softmax(attn_weights, dim=2)  # Softmax over time dimension
        weighted = x * attn_weights  # Apply attention weights
        out = weighted.sum(dim=2)  # Sum over time dimension
        return out  # shape: (batch_size, num_channels, hidden_size)


class MCRAS(nn.Module):
    """
    Multi-Channel Recurrent Attention System
    """
    def __init__(self, input_size, hidden_size, num_channels, num_classes, rnn_type='LSTM'):
        super(MCRAS, self).__init__()
        self.num_channels = num_channels
        self.hidden_size = hidden_size

        # Define RNN for each channel
        self.rnns = nn.ModuleList([
            nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
            if rnn_type == 'LSTM' else nn.GRU(input_size=input_size, hidden_size=hidden_size, batch_first=True)
            for _ in range(num_channels)
        ])

        # Attention layer
        self.attention = AttentionLayer(hidden_size, num_channels)

        # Fully connected output layer
        self.fc = nn.Linear(num_channels * hidden_size, num_classes)

    def forward(self, x):
        """
        x shape: (batch_size, num_channels, seq_len, input_size)
        """
        channel_outputs = []

        for i in range(self.num_channels):
            rnn_out, _ = self.rnns[i](x[:, i, :, :])  # shape: (batch_size, seq_len, hidden_size)
            rnn_out = rnn_out.unsqueeze(1)  # shape: (batch_size, 1, seq_len, hidden_size)
            channel_outputs.append(rnn_out)

        # Concatenate channel outputs
        combined = torch.cat(channel_outputs, dim=1)  # shape: (batch_size, num_channels, seq_len, hidden_size)

        # Apply attention
        attn_out = self.attention(combined)  # shape: (batch_size, num_channels, hidden_size)

        # Flatten channels
        attn_out = attn_out.view(attn_out.size(0), -1)  # shape: (batch_size, num_channels*hidden_size)

        # Final output
        out = self.fc(attn_out)  # shape: (batch_size, num_classes)
        return out
