#Allows you to ask a question and the answer is based off of a faq file
from bottle import route, post, run, request
import sqlite3
import os
import ollama
import requests
from bs4 import BeautifulSoup

#Class For Interacting with Database
#path() is used for using database in same folder as script
class database:
    def path():
        current_directory = os.path.dirname(os.path.abspath(__file__))
        db_name = 'blog.db'
        file_path = os.path.join(current_directory, db_name)

        return file_path

    def db_create():
        file_path = database.path()
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        create_table = '''
                        create table if not exists entry(
                            id integer primary key,
                            title text,
                            post text
                        )
                        '''

        cursor.execute(create_table)
        conn.commit()
        conn.close()

    def db_select():
        file_path = database.path()
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        sql = 'select * from entry order by id desc'
        cursor.execute(sql)
        record = cursor.fetchall()
        conn.commit()
        conn.close()

        return record

    def db_insert(title, post):

        file_path = database.path()
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        sql = 'insert into entry(title, post) values(?,?)'
        cursor.execute(sql,(title, post))
        conn.commit()
        conn.close()

#Scrape the Title and the Text of the post
def parse(url):
    response = requests.get(url)
    response.raise_for_status()  # This will raise an exception if there's an error.

    soup = BeautifulSoup(response.text, 'html.parser')

    p_tags = soup.find_all('p')
    title = soup.find('title')

    page_title = title.text
    page_text=''
    for p in p_tags:
        page_text = f'{page_text} {p.text}'

    return page_title,page_text 

#LLM Function - Write the title
def write_title(post_title):
    query = f'''rewrite this title for a blog post\
            -- give only one response \
            -- do not say anything such as  -- Heres a possible rewrite of the title for a blog post:\
            -- {post_title}'''
    response = ollama.chat(model='llama2:13b', messages=[
    {
        'role': 'user',
        'content': query,
    },
    ])
    response = response['message']['content']

    return response

#LLM Function - Write the post
def write_post(post_text):
    query = f'Write a 500 word blog post based on this information\
            -- do not add a title \
            -- do not say anything such as "this article" \
            -- {post_text}'
    response = ollama.chat(model='llama2:13b', messages=[
    {
        'role': 'user',
        'content': query,
    },
    ])
    response = response['message']['content']

    return response

#Index Page. Query form sends values back to this page
@route('/')
@post('/')
def index():
    url = request.forms.get('url')

    #Scape Web Page, Clean up text, send to LLM
    if url != None:
        response = parse(url) #response[0] = Title, resposne[1] = Post
        print(response[0])
        print(response[1])
        title = write_title(response[0])

        #Clean up the Title returned from LLM.  This works for llama2
        title = title.split(':')
        title = title[1]
        title = title.replace('"','')
        print(f'TITLE --- {title}')

        #Wrap Post Paragagraphs in <p> tags
        post=''
        post_raw = write_post(response[1])
        post_list = post_raw.split('\n')
        for item in post_list:
            post = f'{post} <p>{item}</p>'
        print(f'POST ---- {post}')
        database.db_insert(title, post)

    #Add data to database
    record_set = database.db_select()

    form =  f'''
                <form action="./" method="post">
                URL: <textarea cols="50" rows="1" name="url"></textarea>
                <br>
                <input type="submit">
                </form>
            '''
    
    #Create feed of previous posts
    previous=''
    for record in record_set:
        previous =f'''
                        {previous} 
                        <h1>{record[1]}</h1>
                        {record[2]}
                        <hr>
                    '''
    
    page = f'''
                {form}
                {previous}
            '''

    return page

#Create database table if it does not exist
database.db_create()

#Run web server.  If post 80 does not work try 8080
run(host='0.0.0.0', port=80, debug=True)