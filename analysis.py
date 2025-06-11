import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load chat history from SQLite
def load_data():
    conn = sqlite3.connect('chat_history.db')
    query = "SELECT id, user_message, bot_response, timestamp FROM chat_history"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df

# Analyze helpful vs unhelpful responses
def analyze_helpfulness(df):
    df['is_helpful'] = ~df['bot_response'].str.contains("don't know|not sure", case=False, na=True)
    helpful_count = df['is_helpful'].sum()
    unhelpful_count = len(df) - helpful_count

    plt.figure(figsize=(6, 6))
    plt.pie([helpful_count, unhelpful_count],
            labels=['Helpful', 'Unhelpful'],
            autopct='%1.1f%%',
            colors=['#4CAF50', '#F44336'])
    plt.title("Chatbot Helpfulness")
    plt.savefig("helpfulness_chart.png")
    plt.show()

# Analyze top keywords in user messages
def analyze_keywords(df):
    keywords = ['career', 'job', 'skill', 'course', 'education', 'interview', 'resume']
    keyword_counts = {k: 0 for k in keywords}
    for msg in df['user_message']:
        for keyword in keywords:
            if keyword in msg.lower():
                keyword_counts[keyword] += 1

    keyword_df = pd.DataFrame.from_dict(keyword_counts, orient='index', columns=['Count']).sort_values(by='Count', ascending=False)

    plt.figure(figsize=(10, 6))
    sns.barplot(x=keyword_df['Count'], y=keyword_df.index, palette='viridis')
    plt.title("Top Keywords in User Messages")
    plt.xlabel("Frequency")
    plt.ylabel("Keyword")
    plt.tight_layout()
    plt.savefig("keyword_analysis.png")
    plt.show()

# Chat activity by time of day
def analyze_activity_by_hour(df):
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='hour', palette='coolwarm')
    plt.title("Chat Activity by Hour of Day")
    plt.xlabel("Hour of Day")
    plt.ylabel("Number of Messages")
    plt.tight_layout()
    plt.savefig("activity_by_hour.png")
    plt.show()

# Chat activity by day of week
def analyze_activity_by_day(df):
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=day_order, ordered=True)
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x='day_of_week', palette='magma')
    plt.title("Chat Activity by Day of Week")
    plt.xlabel("Day of Week")
    plt.ylabel("Number of Messages")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("activity_by_day.png")
    plt.show()

# Detect how often search links are used
def analyze_search_usage(df):
    df['has_link'] = df['bot_response'].str.contains("https://",  na=False)
    link_count = df['has_link'].sum()
    no_link_count = len(df) - link_count

    plt.figure(figsize=(6, 6))
    plt.pie([link_count, no_link_count],
            labels=['With Resource Links', 'No Links'],
            autopct='%1.1f%%',
            colors=['#2196F3', '#FFEB3B'])
    plt.title("Responses with External Resources")
    plt.savefig("search_link_usage.png")
    plt.show()

# Main function to run all analyses
def main():
    df = load_data()
    analyze_helpfulness(df)
    analyze_keywords(df)
    analyze_activity_by_hour(df)
    analyze_activity_by_day(df)
    analyze_search_usage(df)

if __name__ == "__main__":
    main()