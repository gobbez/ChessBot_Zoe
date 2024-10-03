import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dropout, Flatten, Dense, Embedding, LSTM
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical, pad_sequences
import zstandard as zstd
import json
import io
from pathlib import Path
from sklearn.preprocessing import LabelEncoder

THIS_FOLDER = Path(__file__).parent.resolve()
lichess_2013_jan_file = THIS_FOLDER / "github/ChessBot_Zoe/database/lichess_db_standard_rated_2013-01.pgn.zst"
lichess_2013_jan_csv = THIS_FOLDER / "github/ChessBot_Zoe/database/lichess_2013_jan_csv.csv"

def workon_lichess():
    """
    This function loads the Lichess-jan-2013 database and creates a Deep Learning model to learn how to play chess
    Objective: learn chess moves
    """
    # Check if a model is already created
    check_model = 0
    select_name_model = 'lichess_2013_jan.h5'
    try:
        model = load_model('lichess_2013_jan.h5')
        select_new = 0
        if select_new == '1':
            select_name_model = input('Type the name of the new model: ')
            check_model = 0
        else:
            check_model = 1
    except:
        print('No model loaded. Proceed to creating, training and saving a new one')
        check_model = 0

    if check_model == 0:
        check_csv = 0
        # Load Lichess db
        try:
            df_moves = pd.read_csv(lichess_2013_jan_csv)
            check_csv = 1
        except:
            print('No file csv saved. Proceed to creating, cleaning and saving a new one')
            check_csv = 0

        if check_csv == 0:
            # Create csv file loading Lichess user DataBase
            with open(lichess_2013_jan_file, 'rb') as compressed_file:
                dctx = zstd.ZstdDecompressor()
                decompressed = dctx.stream_reader(compressed_file)
                file_stream = io.TextIOWrapper(decompressed, encoding='utf-8')
                # Variabile per memorizzare le informazioni desiderate
                list_event = []
                list_WhiteElo = []
                list_BlackElo = []
                list_TimeControl = []
                list_moves = []

                for line in file_stream:
                    line = line.strip()  # Rimuovi gli spazi bianchi all'inizio e alla fine

                    # Controlla se la linea contiene le chiavi desiderate
                    if line.startswith("[Event"):
                        line = line.replace('[Event', '')
                        line = line.replace('game', '')
                        line = line[:-3]
                        line = line.replace('"', '')
                        list_event.append(line)
                    elif line.startswith("[WhiteElo"):
                        line = line.replace('[WhiteElo', '')
                        line = line.replace('"', '')
                        line = line.replace(']', '')
                        line = line.replace('?', '')
                        line = line.replace(' ', '')
                        list_WhiteElo.append(line)
                    elif line.startswith("[BlackElo"):
                        line = line.replace('[BlackElo', '')
                        line = line.replace('"', '')
                        line = line.replace(']', '')
                        line = line.replace('?', '')
                        line = line.replace(' ', '')
                        list_BlackElo.append(line)
                    elif line.startswith("[TimeControl"):
                        line = line.replace('[TimeControl', '')
                        line = line.replace(' ', '')
                        line = line.replace('"', '')
                        if len(line) > 3 and line[3] == '+':
                            line = line[:3]
                        elif len(line) > 2 and line[2] == '+':
                            line = line[:2]
                        elif len(line) > 1 and line[1] == '+':
                            line = line[:1]
                        else:
                            line = line[0]
                        list_TimeControl.append(line)
                    elif line and not line.startswith("["):
                        list_moves.append(line)

                df_moves = pd.DataFrame({'Event': list_event, 'WhiteElo': list_WhiteElo, 'BlackElo': list_BlackElo,
                                        'TimeControl': list_TimeControl, 'Moves': list_moves})

                # Clean DataFrame
                df_moves = df_moves.dropna()
                df_moves = df_moves[(df_moves != '').all(axis=1)]
                df_moves['WhiteElo'] = df_moves['WhiteElo'].astype('int')
                df_moves['BlackElo'] = df_moves['BlackElo'].astype('int')
                # Save DataFrame
                df_moves.to_csv('lichess_2013_jan_csv.csv')

        df_moves = df_moves.drop(columns=['Unnamed: 0'])

        # Set X and y
        SEED = 42
        X = df_moves[['WhiteElo', 'BlackElo']]
        y = df_moves['Moves']

        # Encode the moves as sequences of numbers
        tokenizer = LabelEncoder()
        tokenizer.fit(y)
        y = tokenizer.transform(y)

        # Pad sequences to ensure they all have the same length
        y = pad_sequences(y.reshape(-1, 1), padding='post')

        # Set train and test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=SEED)

        # Normalyze Data
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        # Define Sequential model
        model = Sequential()

        # Neural Network
        model = Sequential()
        model.add(LSTM(128, input_shape=(X_train.shape[1], 1), return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(64, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(32, activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(len(tokenizer.classes_), activation='softmax'))

        # Compile the model and use accuracy as metrics
        model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

        # Define EarlyStopping to prevent to continue after it's not improving anymore (so less chance of OverFitting)
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

        # Train the model with 100 epochs
        history = model.fit(X_train, y_train, epochs=100, validation_data=(X_test, y_test), callbacks=[early_stopping])

        # Save model
        model.save(select_name_model)


        # Plot trend of loss and accuracy for both train and test
        plt.figure(figsize=(12, 6))

        # Loss
        plt.subplot(1, 2, 1)
        plt.plot(history.history['loss'], label='Train Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Loss')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()

        # Accuracy
        plt.subplot(1, 2, 2)
        plt.plot(history.history['accuracy'], label='Train Accuracy')
        plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
        plt.title('Accuracy')
        plt.xlabel('Epochs')
        plt.ylabel('Accuracy')
        plt.legend()

        plt.show()

        # Create previsions on test data
        y_pred = model.predict(X_test)
        y_pred_classes = np.argmax(y_pred, axis=1)

        # Check previsions with original data
        accuracy = np.mean(y_pred_classes == y_test.argmax(axis=1))
        print(f'Accuracy on test set: {accuracy:.4f}')

workon_lichess()
