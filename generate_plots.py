import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import numpy as np

def get_top_terms_per_cluster(vectorizer, kmeans, n_terms=10):
    """
    Get the top terms per cluster from the KMeans clustering.
    """
    terms = vectorizer.get_feature_names_out()
    centroids = kmeans.cluster_centers_
    top_terms = []

    for i, centroid in enumerate(centroids):
        # Get the indices of the top terms
        top_indices = centroid.argsort()[-n_terms:][::-1]
        top_terms.append([terms[index] for index in top_indices])
    
    return top_terms

def generate_complaint_plots():
    # Connect to the SQLite database
    conn = sqlite3.connect('complaints.db')

    # Query to get data from the complaints table
    query = "SELECT specific_issue FROM complaints"
    df = pd.read_sql_query(query, conn)

    # Close the connection
    conn.close()

    # Initialize TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(stop_words='english')

    # Fit and transform the complaint data
    X = vectorizer.fit_transform(df['specific_issue'])

    # Number of clusters (adjust as needed)
    num_clusters = 5

    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    clusters = kmeans.fit_predict(X)

    # Add cluster labels to the DataFrame
    df['cluster'] = clusters

    # Count the number of complaints per cluster
    cluster_counts = df['cluster'].value_counts()

    # Get top terms for each cluster
    top_terms = get_top_terms_per_cluster(vectorizer, kmeans)

    # Plot the results
    plt.figure(figsize=(12, 6))
    cluster_counts.plot(kind='bar', color='skyblue')
    plt.title('Number of Complaints per Category')
    plt.xlabel('Category')
    plt.ylabel('Number of Complaints')
    plt.xticks(ticks=range(num_clusters), labels=[', '.join(terms) for terms in top_terms], rotation=45)
    
    # Save the plot
    plt.savefig('static/plots/complaint_categories.png')
    plt.close()

if __name__ == "__main__":
    generate_complaint_plots()
