github: 
    cd C:\mma
    git init
    git add .
    git commit -m "Initial commit"
    git remote add origin https://github.com/roachhuang/mma.git
    git branch -M main
    git push -u origin main
# ssh located at ~/.ssh/
If the repository already contains a README or other files, you may need to pull those changes first:
git pull origin main --allow-unrelated-histories
git push -u origin main


virtualenv
https://hackmd.io/ouzfodBiR7asRZspTXdq2Q

# pymoney

auto py investment recommendation for paid subscribers

# pd.set_option("display.max_rows", None)
# pd.set_option("display.max_columns", None)
# Print the DataFrame
# print(df)
# Reset to default options after debugging
# pd.reset_option("display.max_rows")
# pd.reset_option("display.max_columns")

# for better comparison, normalize price data so that all prices start at 1.0    
# if plt misplt, check if date is unique.
# print(df.index.is_unique) 

# Mutable objects (e.g., lists, dictionaries, sets): Avoid chain assignment unless you explicitly want them to share the same reference.

df0050.loc['2024-01-01':'2024-02-01']
df0050.dropna()
df0050.fillna(method:'ffill')
df0050.fillna(method:'bfill')



a&s
7ctn2iRqnbcC5k7X2tkxHZEcBUVNbsLHhmWYSPqA3Nbr
8o7DB5fm8fBuK97JdXoXMQoWQTKoykLTgFdfsoCTYN7j

linenotify:
tkn: p5aTOL8g2SLA5q4PSciN5bz4u04GssMeAEWZ3uFZkVf


mongosh
    show dbs
    use <database>
    db.<collection>.insertOne({x:1})
    db.<collection>.find({'title':'titanic'})
    use sample_mflix

    db.movies.find( { rated: { $in: [ "PG", "PG-13" ] } } )
    use sample_mflix

    db.movies.find( { countries: "Mexico", "imdb.rating": { $gte: 7 } } )


    yfinance returns pandas dataframe
# conver pd to mongodb. data is a dataframe
data_dict = data.to_dict('records)
# MongoDB accepts data in JSON format (key, value pairs) that is nothing but Python dictionary.
collection.insert_many(data_dict)

mongodb to pd
cursor = mycollection.find() 
# Converting cursor to the list of dictionaries 
list_cur = list(cursor)
if len(list_cur > 0): 
    # Converting to the DataFrame 
    df = DataFrame(list_cur)

db.getCollection(collectionName).countDocuments()

mongosh
    show dbs
    use <database>
    db.<collection>.insertOne({x:1})
    db.<collection>.find({'title':'titanic'})
    use sample_mflix

    db.movies.find( { rated: { $in: [ "PG", "PG-13" ] } } )
    use sample_mflix

    db.movies.find( { countries: "Mexico", "imdb.rating": { $gte: 7 } } )

# BASIC_PYTHON_TRADING_BOOK
BASIC_PYTHON_TRADING_BOOK

mongosh    
    show dbs
    use <db>
    db.dropDatabase()

    show collections
    db.<collection>.find()
    db.<collection>.drop()
    
db.getCollection(collectionName).countDocuments()

    
