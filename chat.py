import ast
import json
import re
from openai import OpenAI
import streamlit as st
import os
from urllib.parse import urlparse
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


def extract_query_parameters(content):
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, content)
    if match:
        full_url = match.group(0)
        # Parse the URL to get query parameters
        parsed_url = urlparse(full_url)
        relative_url = f"{parsed_url.path}?{parsed_url.query}" if parsed_url.query else parsed_url.path
        return relative_url
    return None

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
                        if "product" in message and message["product"] is None:
                             st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                             st.markdown("No image found")

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




# Function to handle chat interaction
def handle_chat_interaction(prompt):
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    user_messages_count = len(user_messages)
    category = st.session_state.selected_tab
    print(category)
    
    st.session_state.messages.append({"role": "user","Qno":user_messages_count, "content": prompt,"category":st.session_state.selected_tab})
    
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(f"**Qno {user_messages_count+1}:** {prompt}")

    last_prompt = []
    category_prompts = {
    "Bra": """
   i want answers related to shyaway.com alone
   category = Bra
   offers=buy-3-for-1199,buy-2-for-1299,flat-20%-off,buy-3-for-899,flat-50%-off,flat-40%-off,new-arrival
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints
   fabric=Nylon,Viscose-Spandex,Nylon-Polyester-Spandex,Cotton,Cotton-Spandex,Lace,Mesh,Modal,Polyester-Spandex,Polycotton-Spandex,Satin
   bra-type=Beginners,Bralette,Cami,Everyday,Fashion-Fancy,Minimiser,Push-Up,T-Shirt
   bra-feature=Backless,Bridal,Casual,Designer,Fancy-Back,Front-Open,Hi-Support,Lacework,Longline,Moulded,No-Sag,Plus-Size,Printed,Sexy,Sleep,Transparent
   bra-coverage=full-coverage,3-4-th-Coverage,Demi-Coverage
   bra-padding=Non-Padded,Padded,Removable-Padding,Lightly-Padded
   bra-wiring=wired,wirefree
   bra-cup-shape=Balconette,Balcony,Full-Cup,Plunge,T-Shirt-Cup
   bra-push-up-level=level-1,level-2,level-3
   bra-closure=back-closure,front-closure,slip-on
   brand=susie,taabu,shyle,shyaway
   size=30a,30b,30c,30d,30dd,32a,32b,32c,32d,32dd,34a,34b,34c,34d,34dd,36a,36b,36c,36d,36dd,38a,38b,38c,38d,38dd,40a,40b,40c,40d,40dd,42a,42b,42c,42d,42dd,44a,44b,44c,44d,44dd,46a,46b,46c,46d,46dd,48a,48b,48c,48d,48dd,50a,50b,50c,50d,50dd,52a,52b,52c,52d,52dd
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "Panty": """
   category = Panty
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   brand=susie,taabu,shyle,shyaway
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=2xl,2xl-3xl,3xl,4xl,5xl,l,l-xl,m,s,s-m,xl,xs,xxl
   fabric=cotton-spandex,disposable,lace,mesh,modal,nylon,nylon-spandex,polycotton-spandex,polyester-spandex,viscose-spandex
   panty-type=bikini,boy-shorts,cycling-shorts,hipster,period-panty,thong,tummy-tucker
   panty-feature=bridal,casual,lacework,maternity,no-vpl,plus-size,printed,seamless,sexy,transparent
   panty-coverage=full-coverage,low-coverage,medium-coverage,no-coverage
   panty-waist-level=high-waist,low-waist,medium-waist
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "lingerie-set":"""
    i want  answers related to shyaway.com alone
    category = lingerie-set
   offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
   size=38D/XL,40B/XXL,40C/XXL,40D/XXL,32D/S,32 D/DD,34 D/DD,36 D/DD,38 D/DD'40 D/DD,42 D/DD,44 D/DD,46 D/DD,48 D/DD,50 D/DD,52 D/DD,54 D/DD,56 D/DD,58 D/DD,2XL/3XL,4XL/5XL
   brand=susie,taabu,shyle
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   fabric=cotton-spandex,lace,mesh,nylon-spandex
   lingerieset-type=everyday,fashion-fancy-bra,push-up,t-shirt
   lingerieset-panty-type=bikini,hipster,thong
   lingerieset-feature=bridal,casual,hi-support,lacework,moulded,no-sag,printed,sexy,Transparent
   lingerieset-panty-feature=bridal,transparent,lacework,,casual,sexy,printed
   lingerieset-bra-closure=back-closure,front-closure,side-closure,slip-on
   lingerieset-bra-coverage=demi-coverage,full-coverage,3/4th-coverage
   lingerieset-panty-coverage=full-coverage,medium-coverage,no-coverage,low-coverage
   lingerieset-bra-padding=padded,non-padded
   lingerieset-bra-wiring=wired,wirefree
   lingerieset-panty-waist-level=hi-impact,low-waist,medium-waist
   lingerieset-bra-seam=seamless,seamed,darted
   lingerieset-bra-cup-shape=balconette,balcony,full-cup,plunge,t-shirt-cup
   lingerieset-push-up-level=level-2,level-3
   lingerieset-bra-straps=back-adjustable,detachable,front-adjustable,fully-adjustable,multiway,non-detachable
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "sportswear": """
    category = sportswear
   offers=flat-20%-off
   size=xs,s,m,l,xl,2xl,3xl,XXL,XXXL
   brand=shyaway,shyle,united-classic,van-heusen
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   sportswear-type=bra,bottoms,tops
   sportswear-feature=racerback,cross-back,leggings,hoodies,seamless,classic-back,crop-top,jackets,shorts,t-back,t-shirt,joggers,skorts,tank
   sportswear-bra-coverage=high-coverage,medium-coverage,low-coverage
   sportswear-bra-impact_level=low-impact,medium-impact,hi-impact
   sportswear-bra-padding=padded,removable-padding
   sportswear-bra-wiring=wirefree
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,  
    "sleepwear": """
    category = sleepwear
   fabric=bamboo,cotton,cotton-spandex,lace,mesh,modal,nylon-spandex,polyester-spandex,satin,viscose
   nightwear-feature=intimate,loungewear,maternity,winter-sleepwear
   nightwear-type=babydoll-and-chemise,camisole-and-slip,tops,nightwear-sets,sleep-tee,sleepwear-bottoms,nightgowns,tops
   color-family=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   offers=buy-2-for-599,flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "shapewear": """
    category = shapewear
   shapewear-type=Saree,Butt Shaper,Tummy Tucker,Body Shaper,Thigh Shaper,Torso Slimmer,Shaping Panty,Mid-Thigh Shaper,Compression Tights
   size=xs,s,m,l,xl,2xl,3xl,4xl,5xl
   brand=mybra,shyle,united-classic
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=nylon-spandex,polycotton-spandex,polyester-spandex,viscose
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "accessories":"""
    category = accessories
   accessories-type=bra-bag,bra-essentials,hosiery,masks,socks,boob-tape,adhesive-stick-on,silicone-nipple-pad,bra-extender
   brand=shyle
   color-family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard
   fabric=cotton-spandex,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   offers=flat-20%-off
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    "clothing":"""
    category = clothing
   clothing-type=Legwear,Scarves,Shrugs & Jackets,Tops
   size=FZ
   brand=shyle
   fabric=cotton-spandex,disposable,elastic,eva,lace,mesh,nylon-spandex,polycotton-spandex,polyester-spandex,silicone
   color-family=black,blue,brown,green,multicolor,orange,pink,prints,red,skin,white,yellow
   offers=flat-10
   price=0-300,1200-1500,1500-1800,300-600,600-900,900-1200
    """,
    
}
    common=f"""
i have provided attributes and attribute values for each category if a question is raised then i need to convert that as attributes and return as output. Find the synonym,understanding the word to match attribute for each word and match with the attribute values and provide the result which should only match with the attribute or category I gave. For example, if i am asking for an apple color bra with 32b size then the result should be like category: {category.lower()},[here]url:https://www.shyaway.com/{category.lower()}-online/?color-family=red,green,size:xl  and if there are more than one attribute value mention that as comma seperated please note that if we have one category then those attribute and attribute values has to be considered like if the question is related to bra then we should consider only those attributes and the common attributes can be used for all categories but dont deviate other than the attribute values i gave
"""
    # common = f"""i have listed out the category and other attributes and if a question is raised then i need to convert that as attributes and return that as output. Find the synonym,understanding the word to match attribute for each word and match with the attribute values and provide the result which should only match with the attribute or category I gave BY JUSTIFYING YOUR SUGGESTION
    # For example, if i am asking for an apple color bra with 32b size then the result should be like category: {category.lower()},[here]url:https://www.shyaway.com/{category.lower()}-online/?color-family=red,green,size=xl  one more example like if we are searching for bamboo bra then since we don't have bamboo we can match than with cotton and provide the result CONSIDER THE WHETHER,TYPE OF SUPPORT AND WHICH ATTRIBUTE SUITS THE QUESTIONS CORRECTLY WITH JUSTIFICATION IN SECOND LINE and if there are more than one attribute value mention that as comma seperated"""
    # #  # Get the specific hello_prompt based on the selected_tab
    hello_prompt = f"{category_prompts.get(st.session_state.selected_tab, "")}{common}"

    print(hello_prompt)
    
    last_prompt.append({"role":"system","content":hello_prompt})
    last_prompt.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        token_place_holder = st.empty
        
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
        url_key = url_key.replace(":","").replace("(","").replace(")","")

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
                if product_details:
                    card(product_details)
                else:
                    st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                    st.markdown("No image found")
            else:
                print("Unexpected response:", data)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "product": product_details,
            "usage":usage_info,
            "category":st.session_state.selected_tab
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




def main():
    # Create placeholders for the title and question count
    title_placeholder = st.empty()
    title_placeholder.title("Shyley")

    # Load chat history
    data = load_chat_history()
    if "messages" not in st.session_state:
        st.session_state.messages = data

    # Sidebar with options
    with st.sidebar:
        # Add a unique key to the button
        if st.button("Delete Chat History", key="delete_chat_history_button"):
            st.session_state.messages = []
            save_chat_history([])
            initialize_hello_prompt()  # Reload the hello prompt

        # Placeholder for question count
        question_count_placeholder = st.empty()
        display_total_question_count(question_count_placeholder)

        st.divider()

        # Initialize selected tab in session state
        if "selected_tab" not in st.session_state:
            st.session_state.selected_tab = "Bra"

        # Use radio buttons to select a tab inside the sidebar
        selected_tab = st.radio(
            "Choose a tab:",
            options=["Bra", "Panty", "lingerie-set","shapewear","clothing","accessories","sportswear","sleepwear"],
            index=["Bra", "Panty", "lingerie-set","shapewear","clothing","accessories","sportswear","sleepwear"].index(st.session_state.selected_tab),
            horizontal=False,  # Set to False to align vertically in the sidebar
            key="sidebar_radio"  # Unique key for sidebar radio
        )

        # Update session state only if the selected tab changes
        if selected_tab != st.session_state.selected_tab:
            st.session_state.selected_tab = selected_tab

        # Display content based on the selected tab
        if st.session_state.selected_tab == "Bra":
            st.subheader("Bra Section")
            st.write("Explore the latest in bras here!")
        elif st.session_state.selected_tab == "Panty":
            st.subheader("Panty Section")
            st.write("Explore the latest in panties here!")
        elif st.session_state.selected_tab == "Lingerie Set":
            st.subheader("Lingerie Set Section")
            st.write("Explore the latest in lingerie sets here!")
        elif st.session_state.selected_tab == "shapewear":
            st.subheader("Shapewear Section")
            st.write("Explore the latest in Shapewear here!")
        elif st.session_state.selected_tab == "clothing":
            st.subheader("Clothing Section")
            st.write("Explore the latest in Clothing here!")
        elif st.session_state.selected_tab == "accessories":
            st.subheader("Accessories Section")
            st.write("Explore the latest in Accessories  here!")
        elif st.session_state.selected_tab == "sportswear":
            st.subheader("Sportswear Section")
            st.write("Explore the latest in Sportswear  here!")
        elif st.session_state.selected_tab == "sleepwear":
            st.subheader("Nightwear Section")
            st.write("Explore the latest in Nightwear here!")

    # Display all chat messages
    display_chat_messages()

    # Main chat input
    if prompt := st.chat_input("How can I help?"):
        handle_chat_interaction(prompt)



if __name__ == "__main__":
    main()
