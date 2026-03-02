no. I clicked on a card and the text was appened. I asked to extend the seatch and a new card was created.

1a. User types in search.  1b. a search query is created and saved to zustand 1b. A card is either selected if possible or it is created. 1c. Zustand is updated as the source of truth. 1d. We update the database with the query 1e. we run the search 1f. We save the source of truth to the database.
2. User types in the chat again. We determine if it is a new search. If it is, we select or create an appropriate card. We update zustand as the source of truth. We update the database with the source of truth
3. User clicks a card. The query is set in zustand as the source of truth. The text from the card is appended to the chat. We run the search. Goto item 2

You need to run this in a browser yourself either w/ playwright or some other borwseruse agent and stop bothering me until everything is working.

everytime something succeeds write a regression test to lock it in.

Do NOT stop until all three steps are perfect.