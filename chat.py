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
                    
                    print(product.get("offer"))
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
                        # if "product" in message and message["product"] is None:
                             # st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                             # st.markdown("No image found")

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
Your the shyaway product assistent shyley. generate a Shyaway product link based on the following details:
    •    If only one detail is provided (e.g., size, color, fabric, etc.), include it as a single parameter in the URL.
    •    If multiple details are given, combine them into a single URL. Ensure all spaces in values are replaced with hyphens (-).

Use the following categories and examples as guidelines:
    1.    Price Range:
price=0 - 300,300 - 600,600 - 900,900 - 1,200,1,200 - 1,500,1,500 - 1,800
Example: https://www.shyaway.com/bra-online/?price=0-499
    2.    Size:
size=32F or size=32B,34C
Example: https://www.shyaway.com/bra-online/?size=32f,34c
    3.    Offers:
offers=buy-3-for-1199,buy-2-for-1299,flat-20%-off,buy-3-for-899,flat-50%-off,flat-40%-off,new-arrival
Example: https://www.shyaway.com/bra-online/?offers=flat-50%-off
    4.    Color:
color-family=Black or color-family=Black, White, Skin, Brown, Yellow, Orange, Pink, Red, Green, Blue, Purple, Prints
Example: https://www.shyaway.com/bra-online/?color-family=blue,pink
    5.    Fabric:
fabric=Nylon, Viscose-Spandex, Nylon-Polyester Spandex, Cotton, Cotton-Spandex, Lace, Mesh, Modal, Polyester-Spandex, Polycotton-Spandex, Satin
Example: https://www.shyaway.com/bra-online/?fabric=nylon,cotton,viscose-spandex
    6.    Other Categories:
    •    Bra Type: bra-type=push-up,t-shirt
    •    Bra Style: bra-feature=backless,bridal
    •    Coverage: bra-coverage=full-coverage
    •    Padding: bra-padding=lightly-padded
    •    Wiring: bra-wiring=wired
    •    Cup Shape: bra-cup-shape=balconette
    •    Push-Up Level: bra-push-up-level=level-1
    •    Closure: bra-closure=back-closure

    7.    Bra Styles:
bra-feature=Backless,Bridal,Casual,Designer,Fancy-Back,Front-Open,Hi-Support,Lacework,Longline,Moulded,No-Sag,Plus-Size,Printed,Sexy,Sleep,Transparent
Example: https://www.shyaway.com/bra-online/?bra-feature=backless,printed
    8.    Bra Types:
bra-type=Beginners, Bralette, Cami, Everyday, Fashion / Fancy, Minimiser, Push-Up, T-Shirt
Example: https://www.shyaway.com/bra-online/?bra-type=Beginners

    9.    Padding:
padding=Non-Padded,Padded,Removable-Padding,Lightly-PaddedBeginners,Bralette,Cami,Everyday,Fashion/Fancy,Minimiser,Push-Up,T-Shirt
Example: https://www.shyaway.com/bra-online/?bra-padding=non-padded,padded
    
    10.Wiring
wiring = wired,wirefree
Example: https://www.shyaway.com/bra-online/?bra-wiring=wired,wirefree

    11.Bra Closure
bra-closure=back-closure,front-closure,slip-on
Example :https://www.shyaway.com/bra-online/?bra-closure=back-closure,front-closure,slip-on
For example, combining multiple details:

Input: size=32B,34C, color=Blue, fabric=Nylon

Output:
https://www.shyaway.com/bra-online/?size=32b,34c&color-family=blue&fabric=nylon

If no relevant link is available, provide the default link:
https://www.shyaway.com/bra-online/
"""
        st.session_state.messages.append({"role": "system", "content": hello_prompt})


# Function to handle chat interaction
def handle_chat_interaction(prompt):
    user_messages = [msg for msg in st.session_state.messages if msg.get("role") == "user"]
    user_messages_count = len(user_messages)
    
    st.session_state.messages.append({"role": "user","Qno":user_messages_count, "content": prompt,"category":st.session_state.selected_tab})
    
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(f"**Qno {user_messages_count+1}:** {prompt}")

    last_prompt = []
    if st.session_state.selected_tab == "Bra":
        hello_prompt ="""
    i want  answers related to shyaway.com alone
    brand=bloom,liberti-world,shyle,vanity-fair,jockey,lovable,enamor,cross-and-pearl,laavian,twin-birds,sonari,inner-sense,susie,amante,united-classic,shyaway,taabu,mybra,libra,nykd-by-nykaa,van-heusen color_family=grey,black,white,skin,brown,yellow,orange,pink,red,green,blue,purple,prints,multicolor,jacquard fabric=bamboo,cotton,cotton-spandex,denim-spandex,disposable,elastic,eva,lace,mesh,modal,nylon-spandex,polyester-spandex,polycotton-spandex,rayon,satin,silicone,viscose,polyamide-spandex,polyester,nylon,viscose-spandex,bamboo-cotton,nylon-polyester-spandex offers=buy-2-for-349,buy-3-for-389,buy-2-for-499,buy-5-for-499,buy-3-for-499,buy-5-for-599,buy-3-for-599,buy-2-for-599,buy-3-for-888,buy-3-for-999,buy-2-for-1049,buy-3-for-1099,buy-2-for-1099,buy-5-for-1199,buy-3-for-1199,buy-6-for-1222,buy-2-for-1299,buy-2-for-1499,buy-2-for-1999,buy-2-for-2499,buy-2-get-2-free,buy-2-get-3-free,combo,flat-10,flat-20percent-off,flat-30,flat-40,buy-4-for-1299,buy-3-get-50percent-off,buy-5-get-60percent-off,buy-1-get-1-free,flat-50percent-off,buy-4-for-999,flat-rs.299,flat-40percent-off,buy-3-for-799,buy-5-for-999,pack-of-5,buy-3-for-899,new-arrival size=42d, 42dd, 44a, 44b, 44c, 44d, 44dd, 46b, 46c, 46d, 46dd, 48b, 48c, 48d, 40a, 40b, 40c, 40d, 40dd, 40z, 42a, 42b, 42c, 38a, 38b, 38c, 38d, 38dd, 38e, 38f, 34d-m, 34a, 34b, 34c, 34d, 34dd, 34e, 34z, 36a, 36b, 36c, 36d, 36dd, 36e, 36z, 30d, 30dd, 32a, 32b, 32c, 32d, 32dd, 36d-l, S, M, L, XL, XXL, 26b, 28b, 28c, 30a, 30b, 30c, 34c-m, 36-xl, 36b-l, 36c-l, 38-xxl, 38b-xl, 38c-xl, 38z, 40-xxxl, 40e, 42z, 44z, FZ, XS, XXXL, 32b-s, 32c-s, 34-l, 34b-m, 30b-s, 32d-m, XXXXL, 30e, 30f, 30g, 30h, 32e, 32f, 32g, 32h, 34f, 34g, 34h, 36f, 36g, 36h, 38g, 38h, 40f, 40g, 40h, 42e, 42f, 42g, 42h, 44e, 44f, 44g, 44h, 46e, 46f, 46g, 46h, 32ddd, 34ddd, 36ddd, 38ddd, 40ddd, 42ddd, 44ddd, 28d, 28dd, 28e, 28a, 28f, 28g, 3xl, 4xl, 46a, 48a, 48dd, 48e, 48f, 48g, 38d-xl, 40b-xxl, 40c-xxl, 40d-xxl, 32d-s, 5xl, 50b, 50c, 50d, 52b, 52c, 52d, 50a, 50dd, 50e, 50f, 50g, 52a, 52dd, 52e, 52f, 52g, 54a, 54b, 54c, 54d, 54dd, 54e, 54f, 54g, 56a, 56b, 56c, 56d, 56dd, 56e, 56f, 56g, 58a, 58b, 58c, 58d, 58dd, 58e, 58f, 58g, 32-ddd, 34-ddd, 36-ddd, 38-ddd, 40-ddd, 42-ddd, 44-ddd, 46-ddd, 48-ddd, 50-ddd, 52-ddd, 54-ddd, 56-ddd, 58-ddd, 2xs, 2xl, 6xl, sm, lxl, 2xl-3xl, 4xl-5xl, 32j, 34i, 34j, 36i, 36j, 38i, 38j, 40i, 40j, 28h, 28i, 28j, 30i, 30j, 32i, 42i, 42j, 44i, 44j, 46i, 46j, 48h, 48i, 48j, 50h, 50i, 50j, 52h, 52i, 52j accessories_type=bra-bag,bra-essentials,hosiery,masks,socks,boob-tape,adhesive-stick-on,silicone-nipple-pad,bra-extender bra_closure=back-closure,front-closure,side-closure,slip-on bra_coverage=3/4th-coverage,demi-coverage,full-coverage,no-coverage bra_cup_shape=plunge,balcony,balconette,full-cup,t-shirt-cup bra_feature=backless,bridal,casual,designer,fancy-back,front-open,hi-support,lacework,longline,moulded,no-sag,plus-size,printed,sexy,sleep,transparent bra_padding=padded,non-padded,removable-padding,lightly-padded bra_push_up_level=level-1,level-2,level-3 bra_seam=darted,seamed,seamless bra_straps=fully-adjustable,non-adjustable,back-adjustable,detachable,multiway,strap-free,front-adjustable,non-detachable,transparent-strap bra_type=everyday,t-shirt,nursing,maternity,bralette,camisole,minimiser,strapless,push-up,beginners,stick-on,cage-and-harness,fashion-fancy,tube bra_wiring=wired,wirefree lingerieset_bra_closure=back-closure,front-closure,side-closure,slip-on lingerieset_bra_coverage=demi-coverage,full-coverage,3/4th-coverage,no-coverage lingerieset_bra_cup_shape=balconette,balcony,full-cup,plunge,t-shirt-cup lingerieset_bra_padding=padded,non-padded,removable-padding lingerieset_bra_seam=seamless,seamed,darted lingerieset_bra_straps=back-adjustable,detachable,front-adjustable,fully-adjustable,multiway,non-adjustable,non-detachable,strap-free,transparent-strap lingerieset_bra_wiring=wired,wirefree lingerieset_feature=backless,bridal,casual,designer,fancy-back,front-open,hi-support,lacework,longline,moulded,no-sag,plus-size,printed,sexy,sleep,transparent lingerieset_panty_coverage=full-coverage,medium-coverage,no-coverage,low-coverage lingerieset_panty_feature=bridal,transparent,lacework,no-vpl,casual,sexy,seamless,printed,plus-size,maternity lingerieset_panty_type=bikini,boy-shorts,cheekini,hipster,period-panty,thong,tummy-tucker,packs,high-waist lingerieset_panty_waist_level=hi-impact,low-waist,medium-waist lingerieset_push_up_level=level-1,level-2,level-3 lingerieset_type=everyday,t-shirt,nursing,maternity,bralette,camisole,minimisers,strapless,push-up,beginners,stick-on,cage-and-harness,fashion-fancy,tube-bra nightwear_feature=intimate,loungewear,maternity,winter-sleepwear nightwear_type=babydoll-and-chemise,camisole-and-slip,tops,nightwear-sets,sleep-tee,sleepwear-bottoms,nightgowns,nightgown panty_coverage=full-coverage,medium-coverage,low-coverage,no-coverage panty_feature=bridal,transparent,lacework,no-vpl,casual,sexy,seamless,printed,plus-size,maternity panty_type=bikini,boy-shorts,cheekini,high-waist-brief,hipster,packs,period-panty,thong,tummy-tucker,cycling-shorts panty_waist_level=high-waist,medium-waist,low-waist sportswear_bra_coverage=high-coverage,medium-coverage,low-coverage sportswear_bra_impact_level=low-impact,medium-impact,hi-impact sportswear_bra_padding=padded,non-padded,removable-padding sportswear_bra_wiring=wired,wirefree sportswear_feature=racerback,cross-back,leggings,hoodies,seamless,classic-back,crop-top,jackets,shorts,t-back,t-shirt,joggers,skorts,tank sportswear_type=bra,bottoms,tops swimwear_feature=one-piece,two-piece swimwear_sleeve_length=3/4-sleeves,full-sleeves,short-sleeves,sleeveless swimwear_type=bikini,body-suit,frock-suit,sarong
    i have listed out the category and other attributes and if a question is raised then i need to convert that as attributes and return that as output. Find the synonym,understanding the word to match attribute for each word and match with the attribute values and provide the result which should only match with the attribute or category I gave BY JUSTIFYING YOUR SUGGESTION
    For example, if i am asking for an apple color bra with 32b size then the result should be like category: bra, color:red, green,size:32b  one more example like if we are searching for bamboo bra then since we don't have bamboo we can match than with cotton and provide the result CONSIDER THE WHETHER,TYPE OF SUPPORT AND WHICH ATTRIBUTE SUITS THE QUESTIONS CORRECTLY WITH JUSTIFICATION IN SECOND LINE and if there are more than one attribute value mention that as comma seperated
        """
    elif st.session_state.selected_tab == "Panty":
         hello_prompt ="""
    i want  answers related to shyaway.com alone
    category=Panty
price=0-300,300-600,600-900,900-1200
offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
brand=susie,taabu,shyle,shyaway
color=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
size=2xl,2xl-3xl,3xl,4xl,5xl,l,l-xl,m,s,s-m,xl,xs,xxl
fabric=cotton-spandex,disposable,lace,mesh,modal,nylon,nylon-spandex,polycotton-spandex,polyester-spandex,viscose-spandex
panty_type=bikini,boy-shorts,cycling-shorts,hipster,period-panty,thong,tummy-tucker
panty_feature=bridal,casual,lacework,maternity,no-vpl,plus-size,printed,seamless,sexy,transparent
panty_coverage=full-coverage,low-coverage,medium-coverage,no-coverage
panty_waist-level=high-waist,low-waist,medium-waist
    i have listed out the category and other attributes and if a question is raised then i need to convert that as attributes and return that as output. Find the synonym,understanding the word to match attribute for each word and match with the attribute values and provide the result which should only match with the attribute or category I gave BY JUSTIFYING YOUR SUGGESTION
    For example, if i am asking for an apple color bra with 32b size then the result should be like category: bra, color:red, green,size:xl  one more example like if we are searching for bamboo bra then since we don't have bamboo we can match than with cotton and provide the result CONSIDER THE WHETHER,TYPE OF SUPPORT AND WHICH ATTRIBUTE SUITS THE QUESTIONS CORRECTLY WITH JUSTIFICATION IN SECOND LINE and if there are more than one attribute value mention that as comma seperated
        """
         
    elif st.session_state.selected_tab == "Lingerie Set":
         hello_prompt ="""
    i want  answers related to shyaway.com alone
    category:lingerie-set
price=0-300,300-600,600-900,900-1200
offers=buy-3-for-499,buy-3-for-599,flat-20%-off,flat-30,new-arrival
brand=susie,taabu,shyle,shyaway
color=Grey,Black,White,Skin,Brown,Yellow,Orange,Pink,Red,Green,Blue,Purple,Prints,multicolor
lingerieset_bra_closure=back-closure,front-closure,side-closure,slip-on
lingerieset_bra_coverage=demi-coverage,full-coverage,3/4th-coverage,no-coverage
lingerieset_bra_cup_shape=balconette,balcony,full-cup,plunge,t-shirt-cup
lingerieset_bra_padding=padded,non-padded,removable-padding
lingerieset_bra_seam=seamless,seamed,darted
lingerieset_bra_straps=back-adjustable,detachable,front-adjustable,fully-adjustable,multiway,non-adjustable,non-detachable,strap-free,transparent-strap
lingerieset_bra_wiring=wired,wirefree
lingerieset_feature=backless,bridal,casual,designer,fancy-back,front-open,hi-support,lacework,longline,moulded,no-sag,plus-size,printed,sexy,sleep,transparent
lingerieset_panty_coverage=full-coverage,medium-coverage,no-coverage,low-coverage
lingerieset_panty_feature=bridal,transparent,lacework,no-vpl,casual,sexy,seamless,printed,plus-size,maternity
lingerieset_panty_type=bikini,boy-shorts,cheekini,hipster,period-panty,thong,tummy-tucker,packs,high-waist
lingerieset_panty_waist_level=hi-impact,low-waist,medium-waist
lingerieset_push_up_level=level-1,level-2,level-3
lingerieset_type=everyday,t-shirt,nursing,maternity,bralette,camisole,minimisers,strapless,push-up,beginners,stick-on,cage-and-harness,fashion-fancy,tube-
size=38D/XL,40B/XXL,40C/XXL,40D/XXL,32D/S,32 D/DD,34 D/DD,36 D/DD,38 D/DD'40 D/DD,42 D/DD,44 D/DD,46 D/DD,48 D/DD,50 D/DD,52 D/DD,54 D/DD,56 D/DD,58 D/DD,2XL/3XL,4XL/5XL
    i have listed out the category and other attributes and if a question is raised then i need to convert that as attributes and return that as output. Find the synonym,understanding the word to match attribute for each word and match with the attribute values and provide the result which should only match with the attribute or category I gave BY JUSTIFYING YOUR SUGGESTION
    For example, if i am asking for an apple color bra with 32 D/DD size then the result should be like category: bra, color:red, green,size:xl  one more example like if we are searching for bamboo bra then since we don't have bamboo we can match than with cotton and provide the result CONSIDER THE WHETHER,TYPE OF SUPPORT AND WHICH ATTRIBUTE SUITS THE QUESTIONS CORRECTLY WITH JUSTIFICATION IN SECOND LINE and if there are more than one attribute value mention that as comma seperated
        """
    last_prompt.append({'role':"system",'content':hello_prompt})
#     assist = [
#  {'role': 'user',
#  'content': 'hi'},
#  {'role': 'assistant',
#  'content': "Hello! I'm Shyley,your Shyaway shopping assistant. How can I help you today? Whether you're looking for a specific type of lingerie,need sizing advice,or want to find the best deals,I'm here to assist you!",'product': None},
#  {'role': 'user',
#  'content': 'hello'},
#  {'role': 'assistant',
#  'content': "Hi there! How can I assist you today with your lingerie shopping? Whether you're searching for a particular style,size, or offer,I'm here to help!",'product': None},
#  {'role': 'user',
#  'content': 'where i buy bra'},
#  {'role': 'assistant',
#  'content': "You can buy a variety of bras online at Shyaway. Whether you're looking for specific sizes,styles,or colors,I can help you find exactly what you need. You can start browsing our collection here: [Shop Bras at Shyaway](https://www.shyaway.com/bra-online/). If you have specific preferences or need assistance,feel free to let me know!",
#  },
#  {'role': 'user',
#  'content': 'i want blue color padded bra it size 32c'},
#  {'role': 'assistant',
#  'content': "Great choice! You can find a blue padded bra in size 32C at Shyaway. Here's a link to start browsing your preferred options: [Shop Blue Padded Bras in Size 32C](https://www.shyaway.com/bra-online/?color-family=blue&bra-padding=padded&size=32c). If there's anything else you need or have any specific preferences,feel free to ask!",
# },
#  {'role': 'user',
#  'content': 'black bra'},
#  {'role': 'assistant',
#  'content': "If you're looking for black bras,you can browse a wide range of styles and types at Shyaway. Whether you desire a padded,non-padded,or any specific style,there's likely an option for you. To explore black bras,you can visit this link: [Shop Black Bras](https://www.shyaway.com/bra-online/?color-family=black). Let me know if you have specific requirements or need further assistance!",},
#  {'role': 'user',
#  'content': 'white color'},
#  {'role': 'assistant',
#  'content': "If you're looking for white bras, Check out this link to find your perfect white bra: [Shop White Bras](https://www.shyaway.com/bra-online/?color-family=white). Let me know if you need help with anything else!",
#  }]

#     last_prompt.extend(assist)
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
                # else:
                #     st.image(image="https://www.shyaway.com/media/wysiwyg/Sorry-no-results-found-350-x-350.jpg",width=360)
                #     st.markdown("No image found")
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
            options=["Bra", "Panty", "Lingerie Set"],
            index=["Bra", "Panty", "Lingerie Set"].index(st.session_state.selected_tab),
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

    # Display all chat messages
    display_chat_messages()

    # Main chat input
    if prompt := st.chat_input("How can I help?"):
        handle_chat_interaction(prompt)



if __name__ == "__main__":
    main()
