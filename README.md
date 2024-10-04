
# ChessBot_Zoe

Lichess Bot for the purpose of studying both chess and Deep Learning..


## Info
This Chess Bot will have different styles. 

### Stockfish 2 million positions (Working)
Analyze up to 2 million (but the database has 98 millions) chess positions with FENs, evals and best move.
Bot will search the current position in it and find the best move (download link in the repo)


### Deep Learning 2 million positions (too low %)

Deep Learning model with the above mentioned 2 million positions database.
This is working, but the training is veeery slow (more than 10 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.


### Deep Learning Users Chess Games (too low %)

Deep Learning model that trains on a database of 120 thousand Lichess games in order to learn how to play.
This is working, but the training is veeery slow (more than 5 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.



For now it uses Stockfish 2 million positions and, if the position isn't found, it just does a random move.
Working to make it improve!

Feel free to comment, and share your suggestions! :)
