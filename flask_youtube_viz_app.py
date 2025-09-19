"""
Flask app (single-file) that:
- Loads a YouTube trending dataset (CSV or zipped CSV).
- Creates template files (index.html, base.html) automatically if not present.
- Shows a webpage where user can select a category_name and visualize different plots.
- Serves plots as PNG images generated with matplotlib/seaborn.

How to run:
1. Put your dataset next to this file and name it `new_IN_youtube_trending_data.csv` (it can be a .zip containing the CSV). 
2. Install requirements: pip install flask pandas matplotlib seaborn
3. Run: python flask_youtube_viz_app.py
4. Open http://127.0.0.1:5000/

Notes:
- The app will attempt to detect zipped CSVs and load them.
- For large datasets, the plotting uses sampling for scatter plots to keep rendering fast.
"""

from flask import Flask, render_template, request, send_file, url_for
import os
import io
import zipfile
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for PNGs
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
DATA_FILENAME = "new_IN_youtube_trending_data.csv"  # change if needed
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

app = Flask(__name__)

# Utility: ensure templates exist (create minimal templates if missing)
BASE_HTML = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>YouTube Viz</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css">
    <style>
      body{font-family: Arial, Helvetica, sans-serif; padding:20px; background:#f7f8fb}
      .container{max-width:1100px;margin:0 auto;background:#fff;padding:20px;border-radius:8px;box-shadow:0 8px 20px rgba(0,0,0,0.08)}
      header{display:flex;align-items:center;justify-content:space-between}
      footer{font-size:0.9rem;color:#666;margin-top:20px}
      .controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
      label{font-weight:600}
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>YouTube Trending Visualizer</h1>
        <small>Flask + Pandas + Seaborn</small>
      </header>
      {% block content %}{% endblock %}
      <footer>Made with ❤️ — select a category and choose a visualization.</footer>
    </div>
  </body>
</html>
'''

INDEX_HTML = '''{% extends 'base.html' %}
{% block content %}
  <section>
    <form method="get" action="/visualize">
      <div class="controls">
        <div>
          <label for="category">Category:</label><br>
          <select id="category" name="category">
            <option value="__all__">-- All Categories --</option>
            {% for c in categories %}
              <option value="{{c}}" {% if c==selected %}selected{% endif %}>{{c}}</option>
            {% endfor %}
          </select>
        </div>

        <div>
          <label for="plot">Visualization:</label><br>
          <select id="plot" name="plot">
            <option value="views_dist">Views Distribution</option>
            <option value="top_categories">Top Categories by Views</option>
            <option value="likes_vs_views">Likes vs Views (scatter)</option>
            <option value="like_ratio">Like Ratio Distribution</option>
            <option value="publish_hour">Uploads by Hour</option>
            <option value="corr">Engagement Correlation</option>
          </select>
        </div>

        <div>
          <label for="sample">Sample size (for scatter):</label><br>
          <input type="number" id="sample" name="sample" value="5000" min="100" max="50000">
        </div>

        <div style="align-self: flex-end">
          <button type="submit">Show</button>
        </div>
      </div>
    </form>

    <hr>

    {% if plot_url %}
      <h3>Visualization: {{ title }}</h3>
      <img src="{{ plot_url }}" alt="plot" style="max-width:100%;height:auto;border:1px solid #ddd;padding:8px;background:#fafafa"/>
    {% else %}
      <p>Select options above and click <strong>Show</strong> to generate a plot.</p>
    {% endif %}

  </section>
{% endblock %}
'''

# Write templates if missing
os.makedirs(TEMPLATES_DIR, exist_ok=True)
base_path = os.path.join(TEMPLATES_DIR, 'base.html')
index_path = os.path.join(TEMPLATES_DIR, 'index.html')
if not os.path.exists(base_path):
    with open(base_path, 'w', encoding='utf-8') as f:
        f.write(BASE_HTML)
if not os.path.exists(index_path):
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(INDEX_HTML)

# Global dataframe cache
DF = None


def load_data(filename):
    """Load dataset, handling zipped CSVs and common encodings."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Data file not found: {filename}")

    # Check if it's a zip file
    with open(filename, 'rb') as f:
        start = f.read(4)
    if start[:2] == b'PK':  # ZIP header
        z = zipfile.ZipFile(filename, 'r')
        csv_names = [n for n in z.namelist() if n.lower().endswith('.csv')]
        target = csv_names[0] if csv_names else z.namelist()[0]
        with z.open(target) as f:
            for enc in ('utf-8', 'utf-8-sig', 'latin1', 'cp1252'):
                try:
                    return pd.read_csv(f, encoding=enc, engine='python')
                except Exception:
                    f.seek(0)
            f.seek(0)
            return pd.read_csv(f, encoding='latin1', engine='python', on_bad_lines='skip')

    # Otherwise normal CSV
    try:
        return pd.read_csv(filename, engine='python')
    except Exception:
        return pd.read_csv(filename, encoding='latin1', engine='python', on_bad_lines='skip')


# Load dataset once at startup
try:
    DF = load_data(DATA_FILENAME)
    if 'category_name' not in DF.columns and 'categoryId' in DF.columns:
        DF['category_name'] = DF['categoryId'].astype(str)
except Exception as e:
    print("Error loading dataset:", e)
    DF = pd.DataFrame()  # fallback


@app.route('/')
def index():
    cats = []
    if DF is not None and 'category_name' in DF.columns:
        cats = sorted(DF['category_name'].dropna().unique().tolist())
    return render_template('index.html', categories=cats, selected=None, plot_url=None, title=None)


@app.route('/visualize')
def visualize():
    category = request.args.get('category', '__all__')
    plot_type = request.args.get('plot', 'views_dist')
    sample_size = int(request.args.get('sample', 5000))

    if DF is None or DF.empty:
        return "Dataframe not loaded or empty. Check server logs.", 500

    title_map = {
        'views_dist': f'Views Distribution ({category if category!="__all__" else "All Categories"})',
        'top_categories': 'Top Categories by Total Views',
        'likes_vs_views': f'Likes vs Views ({category})',
        'like_ratio': f'Like Ratio Distribution ({category})',
        'publish_hour': 'Uploads by Hour',
        'corr': 'Engagement Correlation Heatmap'
    }
    title = title_map.get(plot_type, 'Visualization')

    plot_url = url_for('plot_image', plot=plot_type, category=category, sample=sample_size)

    cats = sorted(DF['category_name'].dropna().unique().tolist())
    return render_template('index.html', categories=cats, selected=category, plot_url=plot_url, title=title)


@app.route('/plot_image')
def plot_image():
    plot_type = request.args.get('plot', 'views_dist')
    category = request.args.get('category', '__all__')
    sample_size = int(request.args.get('sample', 5000))

    if category == '__all__':
        df = DF.copy()
    else:
        df = DF[DF['category_name'] == category].copy()

    if df is None or df.empty:
        fig, ax = plt.subplots(figsize=(6,3))
        ax.text(0.5, 0.5, 'No data for selected category', ha='center', va='center')
        ax.axis('off')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return send_file(buf, mimetype='image/png')

    for col in ['view_count','likes','dislikes','comment_count','like_ratio']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    sns.set_style('whitegrid')
    fig, ax = plt.subplots(figsize=(10,6))

    try:
        if plot_type == 'views_dist':
            sns.histplot(df['view_count'].dropna(), bins=80, ax=ax)
            ax.set_xscale('log')
            ax.set_xlabel('Views (log scale)')
            ax.set_ylabel('Number of Videos')

        elif plot_type == 'top_categories':
            grouped = DF.groupby('category_name')['view_count'].sum().sort_values(ascending=False).head(10)
            sns.barplot(x=grouped.values, y=grouped.index, ax=ax)
            ax.set_xlabel('Total Views')
            ax.set_ylabel('Category')

        elif plot_type == 'likes_vs_views':
            s = df.sample(min(len(df), sample_size))
            sns.scatterplot(data=s, x='view_count', y='likes', alpha=0.4, ax=ax)
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlabel('Views (log)')
            ax.set_ylabel('Likes (log)')

        elif plot_type == 'like_ratio':
            sns.histplot(df['like_ratio'].dropna(), bins=40, kde=True, ax=ax)
            ax.set_xlabel('Like Ratio')
            ax.set_ylabel('Number of Videos')

        elif plot_type == 'publish_hour':
            if 'publish_hour' in df.columns:
                order = list(range(24))
                sns.countplot(data=df, x='publish_hour', order=order, ax=ax)
                ax.set_xlabel('Hour of Day')
                ax.set_ylabel('Number of Uploads')
            else:
                ax.text(0.5, 0.5, 'publish_hour column not available', ha='center')
                ax.axis('off')

        elif plot_type == 'corr':
            cols = [c for c in ['view_count','likes','dislikes','comment_count','like_ratio'] if c in df.columns]
            corr = df[cols].corr()
            sns.heatmap(corr, annot=True, fmt='.2f', cmap='Blues', ax=ax)

        else:
            ax.text(0.5, 0.5, 'Unknown plot type', ha='center')
            ax.axis('off')

    except Exception as e:
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(6,3))
        ax.text(0.5, 0.5, f'Error plotting: {e}', ha='center', va='center')
        ax.axis('off')

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    print('Starting Flask app... make sure', DATA_FILENAME, 'is present in the same folder')
    app.run(debug=True)
