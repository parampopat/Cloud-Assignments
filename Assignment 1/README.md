# Homework-1  
Dining Concierge Agent  

# Contributors
Kartik Balasubramaniam(kb3127) & Param Popat(pvp2109)

# Documentation
**Core Functions**  
```talk_to_lex``` - LF0 - bound with UI. talks to lex through the post API  
```restaurant_suggest.py``` - LF1 - Handles Lex fulfillment. Captures data and sends to SQS  
```lookup_send_text.py``` - LF2 - Read the queue and send the SMS.  
```index.html``` - UI Code
  
**Ancillary Functions**   
```scrap_yelp.py``` - Use Yelp API to scrape data and store in DynamoDB  
```elastic_upload.py``` - Read DynamoDB and upload to elastic Search 
 

