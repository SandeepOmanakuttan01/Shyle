import re
from openai import OpenAI
import streamlit as st
import os
import shelve
import requests
import random
from urllib.parse import urlparse


# Constants
USER_AVATAR = "👤"
BOT_AVATAR = "🤖"


# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Set default OpenAI model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini-2024-07-18"

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
            offer_data{{
              label
              color
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



def extract_query_parameters(content):
    """
    Extracts the query parameters from a plain URL in the given text content.

    Args:
        content (str): Text content containing a URL.

    Returns:
        str: Extracted query parameters or None if no URL or query is found.
    """
    # Regular expression to match a plain URL
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, content)
    if match:
        full_url = match.group(0)
        # Parse the URL to get query parameters
        parsed_url = urlparse(full_url)
        relative_url = f"{parsed_url.path}?{parsed_url.query}" if parsed_url.query else parsed_url.path
        return relative_url
    return None
def card(product_details):
    if product_details is None:
        st.markdown("No releated images found")
    else:
        rows = len(product_details) // 4 + (len(product_details) % 4 > 0)  # Calculate the number of rows

        for row in range(rows):
            cols = st.columns(4, gap="medium")  # 4 columns with equal padding
            for idx, col in enumerate(cols):
                product_idx = row * 4 + idx
                if product_idx < len(product_details):
                    product = product_details[product_idx]

                    # Initialize offer details
                    offer_label = ""
                    offer_color = "#FF5733"  # Default color

                     # Initialize offer details
                    offer_label2 = ""
                    offer_color2 = "#FF5733"  # Default color
                    
                    # Handle 'offer' if it's a list
                    if isinstance(product.get("offer"), list):
                        for i, offer in enumerate(product["offer"]):
                            if isinstance(offer, dict):
                                if(i ==0):
                                    offer_label = offer.get("label", "")
                                    offer_color = offer.get("color", "#FF5733")
                                else:
                                    offer_label2 = offer.get("label", "")
                                    offer_color2 = offer.get("color", "#FF5733")

                    with col:
                        # Dynamically add the offer tag only if `offer_label` is not empty
                        if offer_label2 != "":
                            offer_tag = f"""
                            <div style="position: absolute; bottom: 10px; right: 0px; 
                                background-color: {offer_color}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label}
                            </div>
                            <div style="position: absolute; bottom: 40px; right: 0px; 
                                background-color: {offer_color2}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label2}
                            </div>
                            """
                        elif offer_label:
                            offer_tag = f"""
                            <div style="position: absolute; bottom: 10px; right: 0px; 
                                background-color: {offer_color}; color: white; padding: 4px 8px; 
                                border-radius: 4px; font-size: 12px;">
                                {offer_label}
                            </div>
                            """
                        else:
                            offer_tag= "" 

                        st.markdown(
                            f"""
                            <div style="text-align: center; margin-bottom: 10px; position: relative;">
                                <!-- Product Image -->
                                <img src="{product['image_url']}" 
                                    style="height: 300px; object-fit: cover; border-radius: 8px;" 
                                    alt="Product Image">
                                
                                {offer_tag}
                           
                            </div>
                            <div style="text-align: center;">
                                <!-- Product Link -->
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
                    if "Qno" in message and message["Qno"]:
                         st.markdown(f"**Qno {message['Qno']}:** {message['content']}")
                    else:
                        st.markdown(message["content"])

                if "usage" in message and message["usage"]:
                    usage = message["usage"]
                    st.markdown(
                        f"""
                        **Prompt**:&nbsp;&nbsp;{usage.prompt_tokens} &nbsp;&nbsp;&nbsp;&nbsp;**Answer**:&nbsp;&nbsp;{usage.completion_tokens} &nbsp;&nbsp;&nbsp;&nbsp;**Total**:&nbsp;&nbsp;{usage.total_tokens}
                        """,
                        unsafe_allow_html=True
                    )
                # Display the image if image_url exists
                if "product" in message and message["product"]:
                    product_details = message['product']
                    card(product_details=product_details)



# Function to initialize a "hello" prompt if the history is empty
def initialize_hello_prompt():
    if not st.session_state.messages:
        hello_prompt = """
You are the shyaway product assistant shyley. generate a Shyaway product link based on the following details:
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
bra-feature=backless, bridal, printed
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
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    user_messages_count = len(user_messages)
    st.session_state.messages.append({"role": "user","Qno":user_messages_count, "content": prompt})
    
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(f"**Qno {user_messages_count+1}:** {prompt}")

    last_prompt = []
    last_prompt.append(st.session_state["messages"][0])
    last_prompt.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        
        # Making a non-streaming request
        response = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=last_prompt
        )

        # Access the token usage directly from the response's attribute
        if hasattr(response, 'usage'):
            usage_info = response.usage
    
        full_response = response.choices[0].message.content        
        message_placeholder.markdown(full_response)
        st.markdown(
            f"""
            **Prompt**:&nbsp;&nbsp;{usage_info.prompt_tokens} &nbsp;&nbsp;&nbsp;&nbsp;**Answer**:&nbsp;&nbsp;{usage_info.completion_tokens} &nbsp;&nbsp;&nbsp;&nbsp;**Total**:&nbsp;&nbsp;{usage_info.total_tokens}
            """,
            unsafe_allow_html=True
        )
        
        # Process the URL key
        url_key = extract_relative_url(full_response)
        if url_key is None:
            url_key = extract_query_parameters(full_response)

        product_details = None  # Default value
        if url_key is not None:
            result = get_product_list(url_key, page=1, limit=20)
            data = result
            
            if "data" in data and "getProductList" in data["data"]:
                items = data["data"]["getProductList"]["data"]["items"]
                random_items = random.sample(items, min(len(items), 4))  # Randomly select up to 4 items
                product_details = [
                    {
                        'product_link': item['product_link'],
                        'sku': item['sku'],
                        'image_url': item['image']['url'],
                        'offer': item.get('offer_data', {})
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
            "usage":usage_info
        })

    save_chat_history(st.session_state.messages)

def display_total_question_count(placeholder):
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    total_questions = len(user_messages)+1
    
    # Calculate total tokens used by the user prompts and assistant responses
    total_prompt_tokens = sum(msg["usage"].prompt_tokens for msg in st.session_state.messages if "usage" in msg)
    total_answer_tokens = sum(msg["usage"].completion_tokens for msg in st.session_state.messages if "usage" in msg)
    total_tokens = total_prompt_tokens + total_answer_tokens
    
    # Display the information
    placeholder.markdown(f"""
    **Total Questions Asked**: {total_questions} 

    **Total Prompt Tokens Used**: {total_prompt_tokens}  

    **Total Answer Tokens Used**: {total_answer_tokens}  

    **Total Tokens Used**: {total_tokens}  
    """)




# Main application logic
def main():

     # Create placeholders for the title and question count
    title_placeholder = st.empty()
   
    
        # Display the title and question count at the top
    title_placeholder.title("Shyley")

    data = load_chat_history()
    # Initialize or load chat history
    if "messages" not in st.session_state:
        st.session_state.messages = data

    # display_total_question_count(question_count_placeholder)


  # Assign a sequential number starting from 1
    # Load default hello prompt if history is empty
    initialize_hello_prompt()

    st.session_state.message = []
    # # Sidebar with a button to delete chat history
    with st.sidebar:
        if st.button("Delete Chat History"):
            st.session_state.messages = []
            save_chat_history([])
            initialize_hello_prompt()  # Reload the hello prompt
        question_count_placeholder = st.empty()
        display_total_question_count(question_count_placeholder)
    
    # save_chat_history(st.session_state.messages)
    
    # # Display all chat messages
    display_chat_messages()

    # # Main chat input
    if prompt := st.chat_input("How can I help?"):
        handle_chat_interaction(prompt)

    



if __name__ == "__main__":
    main()
