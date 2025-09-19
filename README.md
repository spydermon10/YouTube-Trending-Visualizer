# 📊 YouTube Trending Visualizer

A **Flask Web App** that visualizes YouTube trending videos dataset with interactive plots using **Pandas, Matplotlib, and Seaborn**.  
Supports filtering by **video categories** and provides multiple plots for insights.
---

DATASET WAS RETRIEVED FROM KAGGLE (https://www.kaggle.com/datasets/rsrishav/youtube-trending-video-dataset?select=IN_youtube_trending_data.csv)

---

## 🚀 Features
- 📂 Loads CSV or ZIP dataset of trending YouTube videos  
- 🔍 Filter by video **category**  
- 📊 Visualizations:
  - Views Distribution  
  - Top Categories by Views  
  - Likes vs Views (scatter)  
  - Like Ratio Distribution  
  - Uploads by Hour  
  - Engagement Correlation Heatmap  

---

## 📘 Sample Notebook
This repo also contains a sample Jupyter Notebook:  

- **`xyz2.ipynb`** → Demonstrates **data exploration** and provides a better understanding of the dataset and its collection process.  
  Use it to preview the raw structure of the YouTube trending dataset before loading it into the Flask app.  

---

## ⚡ How to Run
1. Place dataset in the same folder:
   - `new_IN_youtube_trending_data.csv` **or** `new_IN_youtube_trending_data.zip`
2. Install dependencies:
   ```bash
   pip install flask pandas matplotlib seaborn


🛠 Tech Stack

Flask (backend & routes)

Pandas (data processing)

Matplotlib & Seaborn (plotting)

HTML + Jinja2 (templates)

Jupyter Notebook (exploratory analysis & dataset understanding)