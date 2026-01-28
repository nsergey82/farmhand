import os
import base64
import json

from flask import Flask, request
from flask_cors import cross_origin
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

app = Flask(__name__, static_folder="", static_url_path="")

PP_SECRET_TOKEN = os.getenv("FARM_JWT_SECRET", "secret")
PUBLIC_PROVISIONER_URL = os.getenv(
    "PUBLIC_PROVISIONER_URL", "http://64.227.64.55:4000/graphql"
)


def _start_client(ename):
    transport = AIOHTTPTransport(
        url=PUBLIC_PROVISIONER_URL,  # strictly we should ask the registry for ename's ip
        headers={"X-ENAME": ename, "Authorization": f"Bearer {PP_SECRET_TOKEN}"},
    )
    return Client(transport=transport)


def _get_state_mid(client):
    query = gql(
        """
        query { 
            findMetaEnvelopesByOntology(ontology: "FarmingState2"){
                id
            }
        }
    """
    )
    result = client.execute(query)
    mes = result["findMetaEnvelopesByOntology"]
    if len(mes):
        return mes[0]["id"]
    return None


def _get_state_id_and_value(client, mid):
    query = gql(
        f"""
        query {{
        getMetaEnvelopeById(id: "{mid}") {{
            id
            ontology
            parsed
            envelopes {{
            id
            ontology
            value
            valueType
            }}
        }}
        }}
        """
    )
    result = client.execute(query)["getMetaEnvelopeById"]["envelopes"]
    data = {}
    for i, envelope in enumerate(result):
        app.logger.debug(f"{i}, {mid}, {envelope}")
        data[envelope["ontology"]] = envelope["value"]

    return (result[0]["id"], data)


def _store_state_value(client, state):
    mutation = gql(
        f"""
            mutation MyMutation1 {{
            storeMetaEnvelope(input: {{
                ontology: "FarmingState2",
                payload: {{
                    state: "{state}"
                }},
                acl: ["*"]}}) {{
                metaEnvelope {{
                id
                ontology
                parsed
                }}
                envelopes {{
                id
                ontology
                value
                valueType
                }}
            }}
            }}
        """
    )
    return client.execute(mutation)


def _update_state_value(client, state_id, state):
    mutation = gql(
        f"""
        mutation MyMutation2 {{
        updateMetaEnvelopeById(
            id: "{state_id}",
            input: {{
                payload: {{ state: "{state}" }}
                ontology: "FarmingState2"
                acl: ["*"]
            }}
            ) {{
            metaEnvelope {{
                id
                ontology
            }}
            envelopes {{
                id
                ontology
                value
                valueType
            }}
            }}
        }}
        """
    )
    return client.execute(mutation)


@app.route("/save/", methods=["POST"])
@cross_origin(allow_headers=["Content-Type"])
def save():
    data = request.get_json()
    ename = data["ename"]
    gamestate = base64.b64encode(json.dumps(data["gamestate"]).encode()).decode("utf-8")
    client = _start_client(ename)
    mid = _get_state_mid(client)
    if mid is not None:
        rc = _update_state_value(client, mid, gamestate)
    else:
        rc = _store_state_value(client, gamestate)
    if len(rc.get("errors", [])):
        app.logger.error(f"Error updating state: {rc.errors}")
        return "Error", 500
    return "OK", 200


def _load(ename: str):
    client = _start_client(ename)
    mid = _get_state_mid(client)
    if mid is None:
        return None
    _, state = _get_state_id_and_value(client, mid)
    return state["state"]


@app.route("/load/<ename>", methods=["GET"])
@cross_origin(allow_headers=["Content-Type"])
def load(ename: str):
    state = _load(ename)
    if state is None:
        return "No saved game", 404
    return state, 200


@app.route("/leaderboard")
def leaderboard():
    enames = [
        "@82f7a77a-f03a-52aa-88fc-1b1e488ad498",
        "@ad0c3d86-c042-59ca-b65f-5454cdaadcb1",
        "@35a31f0d-dd76-5780-b383-29f219fcae99",
    ]
    res = []
    for ename in enames:
        state = _load(ename)
        farm = json.loads(base64.b64decode(state))
        print(farm)
        res.append(
            {
                "ename": ename,
                "farm": farm["farmName"],
                "money": farm["money"],
                "exp": farm["experience"],
                "days": farm["dayCount"],
                "cows": len(farm["cowInventory"]),
            }
        )
    return res


# test with: flask run --host=0.0.0.0 --debug
