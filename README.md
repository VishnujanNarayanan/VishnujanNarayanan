<h1 align="center">Vishnujan Narayanan</h1>

<p align="center">
  <b>Data pipelines, from crawlers to APIs</b><br />
  Data Engineer — Ingestion &amp; Market Data
</p>

<div align="center">

  <!-- shields.io no longer ships a LinkedIn icon, so the logo is inlined as a base64 data URI. -->
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0yMC40NDcgMjAuNDUyaC0zLjU1NHYtNS41NjljMC0xLjMyOC0uMDI3LTMuMDM3LTEuODUyLTMuMDM3LTEuODUzIDAtMi4xMzYgMS40NDUtMi4xMzYgMi45Mzl2NS42NjdIOS4zNTFWOWgzLjQxNHYxLjU2MWguMDQ2Yy40NzctLjkgMS42MzctMS44NSAzLjM3LTEuODUgMy42MDEgMCA0LjI2NyAyLjM3IDQuMjY3IDUuNDU1djYuMjg2ek01LjMzNyA3LjQzM2MtMS4xNDQgMC0yLjA2My0uOTI2LTIuMDYzLTIuMDY1IDAtMS4xMzguOTItMi4wNjMgMi4wNjMtMi4wNjMgMS4xNCAwIDIuMDY0LjkyNSAyLjA2NCAyLjA2MyAwIDEuMTM5LS45MjUgMi4wNjUtMi4wNjQgMi4wNjV6bTEuNzgyIDEzLjAxOUgzLjU1NVY5aDMuNTY0djExLjQ1MnpNMjIuMjI1IDBIMS43NzFDLjc5MiAwIDAgLjc3NCAwIDEuNzI5djIwLjU0MkMwIDIzLjIyNy43OTIgMjQgMS43NzEgMjRoMjAuNDUxQzIzLjIgMjQgMjQgMjMuMjI3IDI0IDIyLjI3MVYxLjcyOUMyNCAuNzc0IDIzLjIgMCAyMi4yMjIgMGguMDAzeiIvPjwvc3ZnPg%3D%3D&logoColor=white)](https://www.linkedin.com/in/vishnujan-narayanan)
  [![Substack](https://img.shields.io/badge/Substack-FF6719?style=for-the-badge&logo=substack&logoColor=white)](https://substack.com/@vishnujannarayanan)
  [![Portfolio](https://img.shields.io/badge/Portfolio-3b5998?style=for-the-badge&logo=google-chrome&logoColor=white)](https://vishnujan.dev/)
  [![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:narayanan.vishnujan@gmail.com)

</div>

---

### About me

I build the crawlers and scheduled jobs that pull data in, the tests that ensure the
data is valid, and the APIs and apps that serve it.

Most of my work starts with a source that doesn't want to hand anything over — APIs
that throttle, portals that change format without warning, pages that only render
what's currently on screen. Around 28 ingestion pipelines in production right now.

The hard part is rarely the first run. It's the second one: whether a rerun repairs
the gaps or quietly corrupts what was already there.

Reach me at **narayanan.vishnujan@gmail.com**

---

### Contribution History

<div align="center">

  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/contributions-dark.svg" />
    <img alt="Contribution history heatmap with animated snake" src="assets/contributions.svg" width="100%" />
  </picture>

</div>

> Generated from the GitHub API by [`scripts/generate_cards.py`](scripts/generate_cards.py) and refreshed
> daily by [`.github/workflows/cards.yml`](.github/workflows/cards.yml) — no third-party image service to go offline.

---

### Projects

<table>
<tr>
<td width="50%" valign="top">

#### [Product Explorer](https://github.com/VishnujanNarayanan/product-explorer)
Full-stack TypeScript app that scrapes a book catalogue into **PostgreSQL** and serves it through Next.js, streaming scrape progress over WebSockets.

`TypeScript` `Playwright` `PostgreSQL`

</td>
<td width="50%" valign="top">

#### [Minute-Level Stock Prediction](https://github.com/VishnujanNarayanan/minute-level-stock-prediction)
Next-minute price direction over **9.4M NSE ticks** — raw trades to minute bars to a directional model, with the leakage traps that make backtests lie.

`scikit-learn` `pandas` `Quant`

</td>
</tr>
<tr>
<td width="50%" valign="top">

#### [Fraud Transaction Detection](https://github.com/VishnujanNarayanan/Fraud_Transaction_Detection)
**6.4M transactions** at a 0.13% fraud rate: 95% of fraud caught at 0.995 ROC-AUC, with the feature engineering that got it there.

`scikit-learn` `Imbalanced Data`

</td>
<td width="50%" valign="top">

#### [Job Application Bot](https://github.com/VishnujanNarayanan/Job_Application_Bot)
Scrapes Indeed, Glassdoor and LinkedIn, scores each posting against a master profile, and builds a tailored résumé per match — served on demand via FastAPI.

`Python` `Playwright` `FastAPI`

</td>
</tr>
<tr>
<td width="50%" valign="top">

#### [Trader Sentiment Analysis](https://github.com/VishnujanNarayanan/Trader_sentiment_analysis)
How the **Bitcoin Fear & Greed Index** moves trader PnL across 211K crypto trades, and a contrarian sentiment-gated signal.

`pandas` `SciPy` `Quant`

</td>
<td width="50%" valign="top">

#### [Support Ticket Classifier](https://github.com/VishnujanNarayanan/ticket-classifier-nlp)
End-to-end NLP — classifies tickets by issue type and urgency, extracts entities, and serves it through a Gradio app.

`NLP` `scikit-learn`

</td>
</tr>
<tr>
<td width="50%" valign="top">

#### [Binance Futures Trading Bot](https://github.com/VishnujanNarayanan/binance-futures-trading-bot)
CLI bot placing market, limit and stop-limit orders against the Binance USDT-M Futures testnet, with position management.

`Python` `API` `Automation`

</td>
<td width="50%" valign="top">

#### [Semantic Quote Retrieval](https://github.com/VishnujanNarayanan/Quotes_Retrieval)
Fine-tuned sentence embeddings over a **FAISS** index of ~2,500 quotes — semantic search that finds matches sharing no keywords.

`FAISS` `sentence-transformers`

</td>
</tr>
</table>

### Fundamentals

Small builds written from scratch, to understand the machinery rather than call it.

<table>
<tr>
<td width="50%" valign="top">

#### [Neural Network From Scratch](https://github.com/VishnujanNarayanan/Neural_net_from_scratch)
Feed-forward classifier in **pure NumPy** — hand-derived backprop, 97.4% accuracy / 0.995 ROC-AUC on Breast-Cancer-Wisconsin.

`NumPy` `Deep Learning`

</td>
<td width="50%" valign="top">

#### [Linear Regression From Scratch](https://github.com/VishnujanNarayanan/Linear_regression_from_scratch)
Gradient descent and a closed-form solver written by hand in **NumPy**, validated against scikit-learn.

`NumPy` `Optimization`

</td>
</tr>
<tr>
<td width="50%" valign="top">

#### [Age & Gender Classifier](https://github.com/VishnujanNarayanan/Image_classifier)
Multi-task CNN predicting age bracket and gender from a face photo, trained on 10,000+ UTKFace images.

`TensorFlow` `Computer Vision`

</td>
</tr>
</table>

<div align="center">
  <a href="https://github.com/VishnujanNarayanan?tab=repositories">
    <img src="https://img.shields.io/badge/See%20all%20repositories-181717?style=for-the-badge&logo=github&logoColor=white" alt="All repositories" />
  </a>
</div>

---

### Tech Stack

**Languages**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=for-the-badge&logo=postgresql&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)

**Backend & Frontend**

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![NestJS](https://img.shields.io/badge/NestJS-E0234E?style=for-the-badge&logo=nestjs&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-5FA04E?style=for-the-badge&logo=nodedotjs&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)

**Infrastructure & Deployment**

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonwebservices&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-FF4438?style=for-the-badge&logo=redis&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)

**Machine Learning & Data**

![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)
![Tableau](https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=tableau&logoColor=white)

---

<div align="center">
  <i>Data in. Products out.</i>
  <br /><br />
  Open to data engineering roles — <b>narayanan.vishnujan@gmail.com</b>
</div>
