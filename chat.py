import ast
import json
import re
from openai import OpenAI
import streamlit as st
import os
import shelve
import requests
import random


# Constants
USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Set default OpenAI model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

# GraphQL endpoint
GRAPHQL_URL = "https://www.shyaway.com/graphql"

# Function to fetch product list
def get_product_list(
    url_key, 
    search_query=None, 
    sort_by="position", 
    sort_direction="asc", 
    page=1, 
    limit=4, 
    token=None
):
    """
    Fetch the product list from the GraphQL API.

    Args:
        url_key (str): URL key for filtering products.
        search_query (str, optional): Search term for product filtering.
        sort_by (str): Sorting criteria ("price", "position", "created_at").
        sort_direction (str): Sort direction ("asc" or "desc").
        page (int): Page number for pagination.
        limit (int): Number of items per page.
        token (str, optional): Authorization token for API access.

    Returns:
        dict: Parsed response containing the product list or an error message.
    """
    # Define the GraphQL query
    query = f"""
    {{
      getProductList(
        urlKey: "{url_key}",
        searchQuery: {f'"{search_query}"' if search_query else "null"},
        sortBy: "{sort_by}",
        sortDirection: "{sort_direction}",
        page: {page},
        limit: {limit}
      ) {{
        status
        message
        data {{
          items {{
            product_link
            sku
            image {{
              url
              width
              height
            }}
          }}
        }}
      }}
    }}
    """

    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Send the request
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)

    # Handle the response
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"HTTP {response.status_code}", "details": response.text}

# Function to load chat history from shelve file
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])


# Function to save chat history to shelve file
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages



def extract_relative_url(content):
    """
    Extracts the relative URL from a Markdown-style link in the given text content.

    Args:
        content (str): Text content containing a URL.

    Returns:
        str: Extracted relative URL or None if no URL is found.
    """
    # Regular expression to match the full URL
    url_pattern = r'\[.*?\]\((https?://[^\)]+)\)'
    match = re.search(url_pattern, content)
    if match:
        full_url = match.group(1)
        # Remove the base URL to get the relative URL
        relative_url = re.sub(r'https?://www\.shyaway\.com/', '', full_url)
        return relative_url
    return None

def card(product_details):
    if product_details is not None:
        rows = len(product_details) // 4 + (len(product_details) % 4 > 0)  # Calculate the number of rows

        for row in range(rows):
            cols = st.columns(4, gap="medium")  # 4 columns with equal padding
            for idx, col in enumerate(cols):
                product_idx = row * 4 + idx
                if product_idx < len(product_details):
                    product = product_details[product_idx]
                    
                    # Display the image with fixed height using HTML
                    with col:
                        st.markdown(
                            f"""
                            <div style="text-align: center; margin-bottom: 10px;">
                                <img src="{product['image_url']}" 
                                    style="height: 300px; object-fit: cover; border-radius: 8px;" 
                                    alt="Product Image">
                            </div>
                            <div style="text-align: center;">
                                <a href="{product['product_link']}" target="_blank" style="
                                    text-decoration: none; 
                                    background-color: #007BFF; 
                                    color: white; 
                                    padding: 8px 12px; 
                                    border-radius: 12px; 
                                    font-size: 14px; 
                                    display: inline-block;">
                                    {product['sku']}
                                </a>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )


def display_chat_messages():
    for i, message in enumerate(st.session_state.messages):
        # Skip the first user message, if necessary
        if i != 0:
            avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
            with st.chat_message(message["role"], avatar=avatar):
                # Display text content if it exists
                if "content" in message and message["content"]:
                    st.markdown(message["content"])
                # Display the image if image_url exists
                if "product" in message and message["product"]:
                    product_details = message['product']
                    card(product_details=product_details)


# Function to initialize a "hello" prompt if the history is empty
def initialize_hello_prompt():
    if not st.session_state.messages:
        hello_prompt = """
Generate a Shyaway product link based on the following details:
	•	If only one detail is provided (e.g., size, color, fabric, etc.), include it as a single parameter in the URL.
	•	If multiple details are given, combine them into a single URL. Ensure all spaces in values are replaced with hyphens (-).

Use the following categories and examples as guidelines:
	1.	Price Range:
price=0-499
Example: https://www.shyaway.com/bra-online/?price=0-499
	2.	Size:
size=32F or size=32B,34C
Example: https://www.shyaway.com/bra-online/?size=32f,34c
	3.	Offers:
offers=Flat-50%-Off
Example: https://www.shyaway.com/bra-online/?offers=flat-50-off
	4.	Color:
color-family=Black or color-family=Blue,Pink,Prints
Example: https://www.shyaway.com/bra-online/?color-family=blue,pink
	5.	Fabric:
fabric=Nylon,Cotton
Example: https://www.shyaway.com/bra-online/?fabric=nylon,cotton
	6.	Other Categories:
	•	Bra Type: bra-type=push-up,t-shirt
	•	Bra Style: bra-feature=backless,bridal
	•	Coverage: bra-coverage=full-coverage
	•	Padding: bra-padding=lightly-padded
	•	Wiring: bra-wiring=wired
	•	Cup Shape: bra-cup-shape=balconette
	•	Push-Up Level: bra-push-up-level=level-1
	•	Closure: bra-closure=back-closure

	7.	Bra Styles:
bra-feature=backless,bridal,printed
Example: https://www.shyaway.com/bra-online/?bra-feature=backless,printed
For example, combining multiple details:

Input: size=32B,34C, color=Blue, fabric=Nylon

Output:
https://www.shyaway.com/bra-online/?size=32b,34c&color-family=blue&fabric=nylon

If no relevant link is available, provide the default link:
https://www.shyaway.com/bra-online/
"""
        st.session_state.messages.append({"role": "assistant", "content": hello_prompt})


# Function to handle chat interaction
def handle_chat_interaction(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    
    last_prompt=[]
    last_prompt.append(st.session_state["messages"][0])
    last_prompt.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        full_response = ""
        for response in client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=last_prompt,
            stream=True,
        ):
            full_response += response.choices[0].delta.content or ""
            message_placeholder.markdown(full_response + "|")
        message_placeholder.markdown(full_response)
        url_key = extract_relative_url(full_response)

        product_details = None  # Default value
        if url_key is not None:
            result = get_product_list(url_key, page=1, limit=20)
            data = result  # If `get_product_list` already returns JSON
            
            if "data" in data and "getProductList" in data["data"]:
                items = data["data"]["getProductList"]["data"]["items"]
                random_items = random.sample(items, min(len(items), 4))  # Randomly select up to 4 items
                product_details = [
                    {
                        'product_link': item['product_link'],
                        'sku': item['sku'],
                        'image_url': item['image']['url']
                    }
                    for item in random_items
                ]

                card(product_details)

            else:
                    print("Unexpected response:", data)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "product": product_details,
        })
    save_chat_history(st.session_state.messages)


# Main application logic
def main():
    st.title("Shyley")

    # Initialize or load chat history
    if "messages" not in st.session_state:
        st.session_state.messages = load_chat_history()

    # Load default hello prompt if history is empty
    initialize_hello_prompt()

    # Sidebar with a button to delete chat history
    with st.sidebar:
        if st.button("Delete Chat History"):
            st.session_state.messages = []
            save_chat_history([])
            initialize_hello_prompt()  # Reload the hello prompt

    # Display all chat messages
    display_chat_messages()

    # Main chat input
    if prompt := st.chat_input("How can I help?"):
        handle_chat_interaction(prompt)


if __name__ == "__main__":
    main()
