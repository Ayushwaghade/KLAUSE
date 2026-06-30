from instagrapi import Client
import sys

def get_followers(username):
    cl = Client()
    # Assuming login session is already handled or saved in the environment
    try:
        user_id = cl.user_id_from_username(username)
        followers = cl.user_followers(user_id)
        for follower in followers:
            print(f'{follower.username}: {follower.full_name}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        get_followers(sys.argv[1])
    else:
        print('Please provide a username.')