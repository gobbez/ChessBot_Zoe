
# ChessBot_Zoe
Lichess Bot for the purpose of studying both chess and Deep Learning.. and challenge the Ranking of Chess-Bots!

<table>
  <tr>
    <td>
      <img src="img/LichessZoeLogo.png" alt="Chess Bot Zoe" width="250" />
    </td>
    <td>
      <h1>Main Features</h1>
      <ul>
        <li>98+ millions chess positions powered by Stockfish, divided by 4 categories (100k - 2m - 10m - 98m positions) (working)</li>
        <li>Different Deep Learning models on its sleeve (not used due to low %)</li>
        <li>Ollama model to chat, interact and even teach user in the game (added soon!)</li>
      </ul>
    </td>
  </tr>
</table>


## Info
This Chess Bot will have different styles. 

### Stockfish million positions: 0.1m - 2m - 10m - 98m (Working)
Analyze up to 98 millions chess positions with FENs, evals and best move and create a pandas DataFrame.
This file uses the Lichess Evaluations .zst file that has up to 98 millions different fens with Stockfish evaluations and best move.
My code will loop through it and extract Fen, Eval and Move (first best move).
My Bot will search the current position in the created DataFrame and find the best move (download link in the repo).

Update: Now there are 4 datasets (respectively with 100k, 2m, 10m, 98m)
Now my Bot will use them based on opponent Elo (but 98m is too slow so it's not using it for real). 
Check "Performances" below to see search speed of each one.


### Deep Learning 2 million positions (too low %)

Deep Learning model with a 2 millions positions database.
This is working, but the training is veeery slow (more than 10 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.


### Deep Learning Users Chess Games (too low %)

Deep Learning model that trains on a database of 120 thousands Lichess games in order to learn how to play.
This is working, but the training is veeery slow (more than 5 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.


### My own chess logic (trying to create a logic from fen - work in progress!)

Since the most of the positions of all these databases are from endgames or finished matches, the bot often fails to get the move.
To solve this i'll try to implement my own chess logic-human-like, from my experience in chess game (and the help of Stockfish too) from fen.


### Ollama Model to Chat, Interact and Teach Users (work in progress!)

The Bot will be powered by Ollama models (maybe Gemma2b) to chat with the user, analyzing position and giving hints.
Nope, even if it wants to teach you, it wants to win at all costs too!


#### Performances
Here are the performances (aka time to execute that part of code) for the 4 possible databases:
Load time is the first time the dataframe is loaded by pandas (only the first time the code is loaded).
Search time it's the time spent to loop searching for FEN and extract best move.

Performances are done searching a starting position with my pc: Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz - 16 Gb Ram
Please note that these times can become a lot more longer in a real game in a complicated (or rare) position when the bot is online.

<table>
  <tr>
    <th>Dataset</th>
    <th>Load Time</th>
    <th>Search Time</th>
  </tr>
  <tr>
    <td>100k positions</td>
    <td>0.1 seconds</td>
    <td>0.6 seconds</td>
  </tr>
  <tr>
    <td>2m positions</td>
    <td>2.2 seconds</td>
    <td>0.9 seconds</td>
  </tr>
  <tr>
    <td>10m positions</td>
    <td>10.9 seconds</td>
    <td>2.2 seconds</td>
  </tr>
  <tr>
    <td>98m positions</td>
    <td>8.9 minutes</td>
    <td>6.5 minutes</td>
  </tr>
</table>



#### Current version

For now it uses one of the 4 datasets based on opponent level in order to recognize and make best move and, if the position isn't found (is it possible?), it just does a random move.
Working to make it improve!


##### Thanks
Feel free to comment, and share your suggestions! :)
