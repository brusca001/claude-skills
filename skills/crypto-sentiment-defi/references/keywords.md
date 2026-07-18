# Crypto Sentiment Keywords (32 Total)

Base list (25) ported verbatim from ClawdBot's crypto-sentiment-analyzer skill (its own reference doc claimed "27 Total" in the header, but the actual keyword list — and the code that runs against it — only ever had 25; corrected here). 7 new keywords added below to close real gaps in the original list and tie in to the other skills built alongside this one.

## Layer 1 Blockchains (7)
Ethereum (ETH), Binance (BNB), Solana (SOL), Ripple (XRP), Cardano (ADA), Avalanche (AVAX), Polkadot

## DeFi Protocols (4)
Uniswap, Aave, Curve Finance, Compound

## Community/Meme Tokens (4)
Dogecoin, Shiba Inu, Floki Inu, Pepe (PEPE)

## Emerging/Layer 2 (5)
Arbitrum, Optimism, Polygon (MATIC), Raydium, AI Tokens

## Macro/Sentiment (2)
Bull Market, Crypto Regulation

## Catch-All Macro (3)
Bitcoin, Cryptocurrency, Altcoin

## Additions (7)
- **Chainlink (LINK)** — major DeFi/oracle protocol, oddly missing from the original DeFi list
- **Base** — Coinbase's L2, one of the most active chains by volume; missing from the original Emerging/L2 list
- **Hyperliquid** — ties directly to the `hyperliquid-backtest` skill running alongside this one; useful to track sentiment on the venue itself
- **Restaking** — covers EigenLayer and the broader restaking narrative, a major 2025-2026 DeFi liquidity theme
- **Pump.fun** — ties to the Solana memecoin sniping bot (`joben-trader`, still running on the VPS); tracks sentiment in that specific ecosystem
- **Airdrop** — perennially high-signal keyword for community/speculative sentiment, absent from the original macro categories
- **ETF** — Bitcoin/Ethereum ETF flow sentiment, one of the biggest macro drivers of 2025-2026 crypto price action

---

## Sentiment Keyword Lexicon

**Bullish**: moon, pump, breakout, hodl, gainer, rally, surge, soar, bull, bounce, green, strong, momentum, bullish, opportunities, bullrun, accumulate, buy, support, reversal, hope, confidence, loading, position, breakthrough, explosive, skyrocket, gain

**Bearish**: crash, dump, risk, decline, margin call, liquidation, bearish, red, weakness, sell, panic, fear, loss, drop, collapse, fall, down, short, resistance, avoid, caution, warning, concern, struggle, pressure

**Neutral**: update, proposal, integration, partnership, adoption, development, analysis, trading, volume, price, level, range, technical, chart, news, announcement, data, report, release

## Spike Detection

50%+ increase over the 7-day rolling baseline = spike alert. Baseline is recalculated daily from `data/sentiment-history.json`.
