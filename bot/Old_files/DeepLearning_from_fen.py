import zstandard as zstd
import json
import io
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import Dropout, Dense
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam


# File paths
THIS_FOLDER = Path(__file__).parent.resolve()
file_path = THIS_FOLDER / "database/lichess_db_eval.jsonl.zst"
csv_path = THIS_FOLDER / "database/2millionmoves.csv"
X_path = THIS_FOLDER / "database/X.csv"
y_path = THIS_FOLDER / "database/y.csv"
model_path = THIS_FOLDER / "database/2million_deeplearning.h5"


def extract_fen():
    """
    Decompress the zst file (with 98m chess positions and evaluations) and extract 2m fens
    :return: pd Dataframe with fens, evaluation and best move
    """
    try:
        df_moves = pd.read_csv(csv_path)
        print('DataFrame found, skip and go to Deep Learning features extraction')
    except:
        print('DataFrame not found. Proceed to creating it')
        with open(file_path, 'rb') as compressed_file:
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.stream_reader(compressed_file)
            text_stream = io.TextIOWrapper(decompressed, encoding='utf-8')

            # Since 98m positions is too much for my pc, i just analyze first 2000000:
            count = 0
            list_fen = []
            list_eval = []
            list_bestmove = []
            for line in text_stream:
                if count <= 2000000:
                    count += 1
                    print(count)
                    record = json.loads(line)

                    # Save results
                    list_fen.append(record['fen'])
                    # Safely access 'cp' or 'mate' key using .get()
                    eval_info = record.get('evals', [{}])[0].get('pvs', [{}])[0]
                    if 'cp' in eval_info:
                        list_eval.append(eval_info['cp'])
                    elif 'mate' in eval_info:
                        mate_value = eval_info['mate']
                        # Convert mate to a high positive or negative value
                        if mate_value > 0:
                            list_eval.append(10000 - mate_value)
                        else:
                            list_eval.append(-10000 - mate_value)
                    # Get 'line' (best move) from eval_info and take only first move
                    list_bestmove.append(eval_info['line'][:4])

                else:
                    # Convert in pd DataFrame and save it as csv
                    df_moves = pd.DataFrame({'Fen': list_fen, 'Eval': list_eval, 'Move': list_bestmove})
                    df_moves.to_csv('2millionmoves.csv')
                    print(df_moves.head())
                    break

    return df_moves


def fen_to_tensor(fen):
    """
    Convert fen in number
    :param fen: fen of the position, from DataFrame
    :return: fen in number
    """
    piece_to_index = {
        'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
        'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11
    }
    tensor = np.zeros((8, 8, 12), dtype=np.float32)
    fen_parts = fen.split(' ')
    rows = fen_parts[0].split('/')
    for row_index, row in enumerate(rows):
        col_index = 0
        for char in row:
            if char.isdigit():
                col_index += int(char)
            else:
                tensor[row_index, col_index, piece_to_index[char]] = 1
                col_index += 1
    return tensor


def get_deeplearning_features(df_moves):
    """
    Converts fen and moves in numbers and normalize evals in order to create Deep Learning features
    :param df_moves: DataFrame of the fen moves csv
    :return: features X and y
    """
    try:
        # Load X e y from csv
        X = np.loadtxt(X_path, delimiter=',')
        y = np.loadtxt(y_path, delimiter=',')
        print('X and y loaded, skip this and go to Deep Learning function')
    except:
        print('X and y not loaded. Proceed to creating and saving them')
        # Convert FENs to tensors
        X_fen = np.array([fen_to_tensor(fen) for fen in df_moves['Fen']])

        # Normalize Eval scores
        eval_scaler = StandardScaler()
        df_moves['Eval_normalized'] = eval_scaler.fit_transform(df_moves[['Eval']])
        X_eval = df_moves[['Eval_normalized']].values

        # Encode moves
        move_encoder = LabelEncoder()
        df_moves['Move_encoded'] = move_encoder.fit_transform(df_moves['Move'])
        y = df_moves['Move_encoded'].values

        # Combine FEN tensors and CP scores
        X_fen = X_fen.reshape((X_fen.shape[0], -1))  # Flatten the tensors
        X = np.hstack((X_fen, X_eval))  # Combine features

        # Save X and y to CSV files
        np.savetxt('X.csv', X, delimiter=',')
        np.savetxt('y.csv', y, delimiter=',')

    return X, y


def deepLearning(X, y):
    """
    Create a Deep Learning model to learn relationships between fen, eval and move to play
    :param X: feature X
    :param y: feature y
    :return:
    """
    # Split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Check if a model is already created
    try:
        model = load_model(model_path)
        print('Model loaded. Proceed to analyze your position')
    except:
        print('No model loaded. Proceed to creating, training and saving a new one')

        # Define model
        num_classes = len(np.unique(y))  # Obtain the number of unique classes in y
        model = Sequential()
        model.add(Dense(512, input_dim=X.shape[1], activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(256, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(128, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(num_classes, activation='softmax'))

        # Compile the model
        model.compile(loss='sparse_categorical_crossentropy', optimizer=Adam(), metrics=['accuracy'])

        # Define EarlyStopping to prevent to continue after it's not improving anymore (so less chance of OverFitting)
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

        # Train the model with 100 epochs
        history = model.fit(X, y, epochs=100, batch_size=32, validation_data=(X_test, y_test), validation_split=0.2, callbacks=[early_stopping])

        # Save model
        model.save('2million_deeplearning.h5')

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



# You have to launch functions in this order:
df_moves = extract_fen()
X, y = get_deeplearning_features(df_moves)
deepLearning(X, y)
