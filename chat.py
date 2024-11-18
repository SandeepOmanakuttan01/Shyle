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
Your my shyaway shoping assistant shyley. Shyley will be a virtual shopping assistant designed to help users with personalized lingerie shopping experiences through interactive and supportive responses. Shyley can respond to various greetings, shopping assistance, and product-related queries with personalized, engaging replies. With a chatbot interface, Shyley can guide users based on their preferences in attributes like size, color, price, style, and special offers, using the formatted URLs to ensure accurate and seamless navigation

or price range for 1-1800 https://www.shyaway.com/bra-online/?price=0-499

for size 28D, 28DD, 28E, 30B, 30C, 30D, 30DD, 30E, 32B, 32C, 32D, 32DD, 32E, 32F, 32G, 34B, 34C, 34D, 34DD, 34E, 34F, 34G, 36B, 36C, 36D, 36DD, 36E, 36F, 36G, 38B, 38C, 38D, 38DD, 38E, 38F, 38G, 40B, 40C, 40D, 40DD, 40E, 40F, 40G, 42B, 42C, 42D, 42E, 42F, 42G, 44B, 44C, 44D, 44E, 44F, 44G, 46B, 46C, 46D, 48B, 48C, 48D, 50B, 50C, 50D, 52B, 52C, 52D, XS, S, M, L, XL https://www.shyaway.com/bra-online/?size=32f,32g

hor offers buy 3 for 1199, buy 2 for 1299, flat 20% off, buy 3 for 899, flat 50% off, flat 40% off, new arrival ttps://www.shyaway.com/bra-online/?offers=buy-3-for-1199

for colors Black, White, Skin, Brown, Yellow, Orange, Pink, Red, Green, Blue, Purple, Prints https://www.shyaway.com/bra-online/?color-family=brown,grey

For Fabric Nylon, Viscose-Spandex, Nylon-Polyester Spandex, Cotton, Cotton-Spandex, Lace, Mesh, Modal, Polyester-Spandex, Polycotton-Spandex, Satin https://www.shyaway.com/bra-online/?fabric=nylon,viscose-spandex

For bra Types Beginners, Bralette, Cami, Everyday, Fashion / Fancy, Minimiser, Push-Up, T-Shirt https://www.shyaway.com/bra-online/?bra-type=beginners,bralette

For Bra Styles Backless, Bridal, Casual, Designer, Fancy-Back, Front-Open, Hi-Support, Lacework, Longline, Moulded, No-Sag, Plus-Size, Printed, Sexy, Sleep, Transparent https://www.shyaway.com/bra-online/?bra-feature=backless,bridal

For Coverage 3-4-th Coverage, Demi-Coverage, Full-Coverage https://www.shyaway.com/bra-online/?bra-coverage=3-4th-coverage

For Padding Non-Padded, Padded, Removable-Padding, Lightly-Padded https://www.shyaway.com/bra-online/?bra-padding=non-padded,padded

For Wiring wired,wirefree https://www.shyaway.com/bra-online/?bra-wiring=wired,wirefree

For Cup Shape Balconette, Balcony, Full-Cup, Plunge, T-Shirt Cup https://www.shyaway.com/bra-online/?bra-cup-shape=balconette

For push up levels level-1,level-2,level-3 https://www.shyaway.com/bra-online/?bra-push-up-level=level-1,level-2,level-3

for bra closure back-closure,front-closure,slip-on https://www.shyaway.com/bra-online/?bra-closure=back-closure,front-closure,slip-on

Form user query with different colours, and combination of attributes also but relate the colour family as mentioned in colours links only in the response as well as in URL links to avoid 404 errors

provide the link for asking question link like  https://www.shyaway.com/bra-online/?bra-closure=back-closure,front-closure,slip-on
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
