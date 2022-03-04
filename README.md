# tinkersLambdaFunction

This is the backend to tinkerscreekflowpredictor.com.

The code in this repo contains 5 different models, one for each hour in the future (t+1,...,t+5). 

Every 10 mins, this function is triggered to run and fetches data using several APIs. Water level from USGS and precipitation data from weatherapi.com are collected and then compared to the current data saved in a DynamoDB table for that hour. If the data does not match, the database is updated.

After update have been made, the function then checks to see if the database contains 5 valid data entries for the past 5 hours to make a prediction. If so, the function uses the pre-trained models to make predictions for the next 5 hours then stores these values in te DynamoDB database.
