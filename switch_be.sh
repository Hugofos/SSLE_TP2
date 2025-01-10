#!/bin/bash

# Read JSON input from stdin
read -r json_input

IP_ADDRESS=$(echo "$json_input" | jq -r '.parameters.alert.data.id' | cut -d':' -f1)

# Check if an IP address was extracted
if [ -z "$IP_ADDRESS" ]; then
    echo "No IP found in the input JSON." | tee -a /var/log/switch_be.log
    exit 1
fi

# Define the endpoint
ENDPOINT="http://$IP_ADDRESS/change_be"

# Make the request
response=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT")

# Check the response status code
if [ "$response" -eq 200 ]; then
    echo "Request to $ENDPOINT was successful."
elif [ "$response" -eq 404 ]; then
    echo "Endpoint $ENDPOINT not found."
elif [ "$response" -eq 500 ]; then
    echo "Server error at $ENDPOINT."
else
    echo "Request to $ENDPOINT returned status code $response."
fi