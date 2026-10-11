import torch
import torch.nn as nn
from dataclasses import dataclass


@dataclass
class PetalConfig:
    vocab_size: int
    max_seq_len: int = 512
    d_model: int = 512
    n_heads: int = 8
    n_layers: int =12
    dropout: float = 0.0


class CausalSelfAttention(nn.Module):

    def __init__(self, config):
        super().__init__()

        self.n_heads = config.n_heads
        self.head_dim = config.d_model // config.n_heads

        self.qkv = nn.Linear(config.d_model, 3 * config.d_model)
        self.out = nn.Linear(config.d_model, config.d_model)

        mask = torch.tril(
            torch.ones(
                config.max_seq_len,
                config.max_seq_len
            )
        )

        self.register_buffer(
            "mask",
            mask.view(
                1,
                1,
                config.max_seq_len,
                config.max_seq_len
            )
        )

    def forward(self, x):

        batch, seq_len, dim = x.shape

        qkv = self.qkv(x)

        q, k, v = qkv.chunk(3, dim=-1)

        q = q.view(
            batch,
            seq_len,
            self.n_heads,
            self.head_dim
        ).transpose(1, 2)

        k = k.view(
            batch,
            seq_len,
            self.n_heads,
            self.head_dim
        ).transpose(1, 2)

        v = v.view(
            batch,
            seq_len,
            self.n_heads,
            self.head_dim
        ).transpose(1, 2)

        attention = (q @ k.transpose(-2, -1)) / (
            self.head_dim ** 0.5
        )

        attention = attention.masked_fill(
            self.mask[:, :, :seq_len, :seq_len] == 0,
            float("-inf")
        )

        attention = torch.softmax(
            attention,
            dim=-1
        )

        output = attention @ v

        output = output.transpose(1, 2).contiguous()

        output = output.view(
            batch,
            seq_len,
            dim
        )

        return self.out(output)


class FeedForward(nn.Module):

    def __init__(self, config):
        super().__init__()

        hidden = 5 * config.d_model

        self.net = nn.Sequential(
            nn.Linear(config.d_model, hidden),
            nn.GELU(),
            nn.Linear(hidden, config.d_model)
        )

    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):

    def __init__(self, config):
        super().__init__()

        self.norm1 = nn.LayerNorm(config.d_model)
        self.attention = CausalSelfAttention(config)

        self.norm2 = nn.LayerNorm(config.d_model)
        self.feed_forward = FeedForward(config)

    def forward(self, x):

        x = x + self.attention(
            self.norm1(x)
        )

        x = x + self.feed_forward(
            self.norm2(x)
        )

        return x


class PetalModel(nn.Module):

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.token_embedding = nn.Embedding(
            config.vocab_size,
            config.d_model
        )

        self.position_embedding = nn.Embedding(
            config.max_seq_len,
            config.d_model
        )

        self.blocks = nn.ModuleList(
            [
                TransformerBlock(config)
                for _ in range(config.n_layers)
            ]
        )

        self.final_norm = nn.LayerNorm(
            config.d_model
        )

        self.lm_head = nn.Linear(
            config.d_model,
            config.vocab_size,
            bias=False
        )

        # Tie input and output embeddings.
        self.lm_head.weight = (
            self.token_embedding.weight
        )

        self.apply(self._init_weights)

    def _init_weights(self, module):

        if isinstance(module, nn.Linear):
            nn.init.normal_(
                module.weight,
                mean=0.0,
                std=0.02
            )

            if module.bias is not None:
                nn.init.zeros_(module.bias)

        elif isinstance(module, nn.Embedding):
            nn.init.normal_(
                module.weight,
                mean=0.0,
                std=0.02
            )

    def forward(self, input_ids):

        batch, seq_len = input_ids.shape

        if seq_len > self.config.max_seq_len:
            raise ValueError(
                "Sequence length exceeds max_seq_len"
            )

        positions = torch.arange(
            seq_len,
            device=input_ids.device
        )

        x = (
            self.token_embedding(input_ids)
            + self.position_embedding(positions)
        )

        for block in self.blocks:
            x = block(x)

        x = self.final_norm(x)

        logits = self.lm_head(x)

        return logits


def count_parameters(model):

    return sum(
        parameter.numel()
        for parameter in model.parameters()
        if parameter.requires_grad
    )


if __name__ == "__main__":

    config = PetalConfig(
        vocab_size=32000
    )

    model = PetalModel(config)

    parameters = count_parameters(model)

    print("=" * 60)
    print("PETAL MODEL")
    print("=" * 60)

    print(
        f"Parameters : {parameters:,}"
    )

    print(
        f"Parameters (M) : {parameters / 1_000_000:.2f}"
    )

    print("=" * 60)