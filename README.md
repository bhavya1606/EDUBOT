# EDUBOT

# How to run ?


### STEPS 

clone the repository

```bash 
Project repo : https://github.com/bhavya1606/EDUBOT

## STEP-01 - create a conda enviroment after opening the repository 

``` bash
conda create -n EDUBOT  python= 3.9 -y

```bash 
conda activate EDUBOT
```

### STEP-02 - install the requirements 
```bash 
pip install -r requirements.txt

### create a `.env` file in the root directory and add your pinecone and grocq or openai CREDENTIAL as follows:
```ini
PINECONE_API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXX'
GROCQ_API_KEY='XXXXXXXXXXXXXXXXXXXXXXXXX'
```

```bash
# run the following command to store embeddings to pinecone
python store_index.py
```

```bash
# finally run the following command
python app.py
```

now 
```bash
open up localhost:
```

### Techstack used:
-python
-langchain
-flask
-gpt
-pinecone

