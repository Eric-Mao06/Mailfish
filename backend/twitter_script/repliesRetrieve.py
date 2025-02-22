import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

url = "https://twitter241.p.rapidapi.com/user-replies-v2"

querystring = {"user": "1543018484170473476", "count": "20"}

headers = {
    "x-rapidapi-key": os.getenv('RAPID_API_KEY'),
    "x-rapidapi-host": "twitter241.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

if response.status_code == 200:
    data = response.json()

    if 'result' in data and 'timeline' in data['result']:
        for instruction in data['result']['timeline']['instructions']:
            if instruction['type'] == 'TimelineAddEntries':
                for entry in instruction['entries']:
                    # Handle regular Timeline Items (Tweets and top-level Replies)
                    if 'itemContent' in entry.get('content', {}):  # Use .get() for safety
                        item_content = entry['content']['itemContent']
                        if 'tweet_results' in item_content and 'result' in item_content['tweet_results']:
                            tweet = item_content['tweet_results']['result']

                            if 'legacy' in tweet:
                                if 'full_text' in tweet['legacy']:
                                    print(f"Tweet: {tweet['legacy']['full_text']}")

                            if 'note_tweet' in tweet:
                                if 'note_tweet_results' in tweet['note_tweet'] and 'result' in tweet['note_tweet']['note_tweet_results']:
                                    if 'text' in tweet['note_tweet']['note_tweet_results']['result']:
                                        print(f"Tweet (Note): {tweet['note_tweet']['note_tweet_results']['result']['text']}")

                            if 'retweeted_status_result' in tweet.get('legacy', {}):  # Safely check
                                retweet = tweet['legacy']['retweeted_status_result']['result']
                                if 'legacy' in retweet and 'full_text' in retweet['legacy']:
                                    print(f"Tweet (Retweet): {retweet['legacy']['full_text']}")
                                if 'note_tweet' in retweet:  # Check for note tweets in retweets
                                    if 'note_tweet_results' in retweet['note_tweet'] and 'result' in retweet['note_tweet']['note_tweet_results']:
                                        if 'text' in retweet['note_tweet']['note_tweet_results']['result']:
                                            print(f"Tweet (Retweet, Note): {retweet['note_tweet']['note_tweet_results']['result']['text']}")

                    # Handle Timeline Modules (Conversations, which can contain nested replies)
                    if 'items' in entry.get('content', {}):   #Use .get()
                        for item_entry in entry['content']['items']:
                            if 'itemContent' in item_entry.get('item',{}): #Use .get()
                                if 'tweet_results' in item_entry['item']['itemContent'] and 'result' in item_entry['item']['itemContent']['tweet_results']:
                                    tweet_or_reply = item_entry['item']['itemContent']['tweet_results']['result']
                                    if 'legacy' in tweet_or_reply and 'full_text' in tweet_or_reply['legacy']:
                                        # Check if in_reply_to_status_id_str exists to identify replies.
                                        if 'in_reply_to_status_id_str' in tweet_or_reply['legacy']:
                                              print(f"  Reply: {tweet_or_reply['legacy']['full_text']}")
                                        else: #if it is not a reply, that means it's the original tweet in that thread
                                              print(f"Tweet: {tweet_or_reply['legacy']['full_text']}")
                                    if 'note_tweet' in tweet_or_reply:
                                        if 'note_tweet_results' in tweet_or_reply['note_tweet'] and 'result' in tweet_or_reply['note_tweet']['note_tweet_results']:
                                            if 'text' in tweet_or_reply['note_tweet']['note_tweet_results']['result']:
                                                print(f"Tweet (Note): {tweet_or_reply['note_tweet']['note_tweet_results']['result']['text']}")


else:
    print(f"Error: {response.status_code} - {response.text}")