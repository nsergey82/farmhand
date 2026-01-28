# Post-platform deployment

We start a Flask backend on port 8194 with something like:
`flask run --host=0.0.0.0 --port 8194`
Don't forget to export the secret token

Then we run `npm start` to start farmhand on port 8080
