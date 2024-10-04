
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
        <li>98+ millions chess positions powered by Stockfish (working)</li>
        <li>Different Deep Learning models on its sleeve (not used due to low %)</li>
        <li>Ollama model to chat, interact and even teach user in the game (added soon!)</li>
      </ul>
    </td>
  </tr>
</table>


## Info
This Chess Bot will have different styles. 

### Stockfish 98 million positions (Working)
Analyze up to 98 millions chess positions with FENs, evals and best move and create a pandas DataFrame.
This file uses the Lichess Evaluations .zst file that has up to 98 millions different fens with Stockfish evaluations and best move.
My code will loop through it and extract Fen, Eval and Move (first best move).
My Bot will search the current position in the created DataFrame and find the best move (download link in the repo)


### Deep Learning 2 million positions (too low %)

Deep Learning model with a 2 millions positions database.
This is working, but the training is veeery slow (more than 10 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.


### Deep Learning Users Chess Games (too low %)

Deep Learning model that trains on a database of 120 thousands Lichess games in order to learn how to play.
This is working, but the training is veeery slow (more than 5 hours) and for the moment very low accuracy. 
I'm stopping this, but you can find the code in the repo.


### Ollama Model to Chat, Interact and Teach Users (work in progress!)

The Bot will be powered by Ollama models (maybe Gemma2b) to chat with the user, analyzing position and giving hints.
Nope, even if it wants to teach you, it wants to win at all costs too!


#### Current version

For now it uses Stockfish 98 million positions to recognize and make best move and, if the position isn't found (is it possible?), it just does a random move.
Working to make it improve!


##### Thanks
Feel free to comment, and share your suggestions! :)
