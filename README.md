
# ChessBot_Zoe
High Performing - Lichess Bot powered by Lichess Human Databases and Stockfish 17 that can vary thinking time and strength level based on opponent Elo and position evaluation.
Telegram Bot to access Lichess Bot results real time!
Human Opening Books to start as an human (work in progress)
Ollama chatbot to interact with users (work in progress)

UPDATE: Now bot can find Opening name and human moves (if the game follows real Lichess games)

<table>
  <tr>
    <td>
      <img src="img/LichessZoeLogo.png" alt="Chess Bot Zoe" width="250" />
    </td>
    <td>
      <h1>Main Features</h1>
      <ul>
        <li>Stockfish 17 that change its thinking time and strength level based on the opponent Elo and position</li>
        <li>Lichess users database to find the most played move by humans and communicate in chat the avg_elo and number of times each move is played</li>
        <li>Tells Opening Name!</li>
        <li>Personalized Opening Repertories to let the Bot follow your preferite lines (work in progress)</li>
        <li>Configure a Telegram Bot to access Lichess Bot games and results.. real time!</li>
        <li>Bot can play multiple games and you can configure bullet too (as of now it's more into rapid or longer)</li>
        <li>You can configure Stockfish thinking time, level or implement other chess logics</li>
        <li>Ollama model to chat, interact and even teach user in the game (work in progress)</li>
      </ul>
    </td>
  </tr>
</table>


## Info
This Chess Bot will have different styles. 

### Stockfish 17 with various levels
Vary its parameters based on opponent elo and how good or bad its position is.
Stockfish can respond in less than 1 second with a pretty good move, but the more time allowed the deeper the analysis.

Before moving, Stockfish will also analyze the position to determine how much more time it needs to spend (aka, the worse its position the more time it will use).
It will also change its strength level to try to stay calibrated towards the opponent level.

You can change Stockfish parameters via Telegram Bot too!


### Lichess Human Moves and Opening Name
For each move, after searching for its Opening Repertories (work in progress), it searches on Lichess Database to find the most played move by human users.
It will also tell you in the chat how many times that move was played and the average Elo of users playing it!

Bot can also tell which Opening is currently playing with the user!


### Personalized Opening Repertories

Bot can follow certain lines of your choose (if you program them) in order to use Stockfish only later in the game.
This can sharp its playing speed (even if Stockfish can answer in less than 1 second too).

Please note that most of the "waiting time" is due to avoid too many Lichess API calls (for now it's 10/20 seconds between moves)


### Play any time

Bot can play every time, but for now only rapid or longer are accepted.


### Ollama Model to Chat, Interact and Teach Users (work in progress!)

The Bot will be powered by Ollama models (maybe Gemma2b:2) to chat with the user, analyzing position and giving hints.
Nope, even if it wants to teach you, it wants to win at all costs too!


### Telegram Bot to access Lichess Bot results LIVE

You can create a Telegram Bot to comunicate with the Lichess Bot and exchange informations. You can set Stockfish level via Telegram, too!


#### Performances
Here are the performances (aka time to execute that part of code):
Stockfish is the time used by Stockfish to answer, Wait time is the time wait to prevent too many Lichess API calls.
These can be configured in the code.

Performances are done on my pc: Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz - 16 Gb Ram.

Please note that these times can become a lot more longer in a real game in a complicated (or rare) position when the bot is online.

<table>
  <tr>
    <th>Stockfish</th>
    <th>Lichess Human moves</th>
    <th>Move wait time</th>
    <th>Ollama chat</th>
  </tr>
  <tr>
    <td>1 / 15 sec</td>
    <td>5 / 10 sec</td>
    <td>10 / 20 sec</td>
    <td>20 / 30 sec</td>
  </tr>
</table>



#### Current version

For now it uses Stockfish with different analysis times and strength level in base of the opponent Elo and position evaluation.
I'm working on adding some specific opening Repertories and Ollama for chat with the user

Working to make it improve!

##### About this repo

Please note that most of the Python files in this repo aren't used. But i left them to track the progresses made and because certain code had potential.


##### Thanks
Feel free to comment, and share your suggestions! :)
