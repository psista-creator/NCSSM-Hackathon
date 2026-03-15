# Reef-Quest
For NCSSM's Annual 2026 Hackathon


## Inspiration
We are witnessing one of the biggest shifts in the Animal Kingdom, as environmental changes in the north and south poles divert many marine species towards deeper bodies of water. Studies by Duke’s Nicholas’s School of the environment reveal that in North Carolina alone, marine populations are resorting to living inside Shipwrecks off the coast in order to escape the conditions of inland lakes and rivers caused by global warming. 

When looking at this issue, we saw one clear problem that affects both humans and marine species: interaction. Marine Scientists in North Carolina will not have enough data if species of fish continue to migrate towards areas which scientists cannot reach, and will not know which man-made sources cause the most harm. This has devastating economic potential for coastal areas, with Cape Pier’s reporting more than 14% less tourism because of the shifting fish populations, which can amount to billions in tourism money over the coming decades. Scientists need more data, while Beaches need more tourism to interact with marine wildlife.

Motivated by the problem at hand, we developed ReefQuest which will connect agencies with real-world data collection sources of marine populations. Allowing for inferences to be made about growing marine populations in specific locations and acting as a key statistic for future plans made by marine associations such as the National Oceanic and Atmospheric Administration (NOAA), and the North Carolina Division of Marine Fisheries (DMF).


## Summarized Problem Statement
- Scientists need more marine biology data from more parts of the world. 
- Beaches need more tourism as people slowly conform to sedentary lifestyle standards, instead of     visiting places teeming with marine wildlife. 
- Secondary effect: Bring Awareness to the deep, unexplored ocean through an engaging game.
- Secondary effect: Scanning fish to collect data on populations in the area, sending it to nuclear plants and national environmental agencies. This will save a lot of their fish management during their water intake process.


## What it does
ReefQuest is a web and desktop-based application that allows users to input pictures and photographs of specific fish populations. Similar to the popular game Pokemon Go, we utilize a database to store fish as “sightings”, encouraging users to explore vast areas of the ocean to document different species of fish. Our rewards system gauges the proportion of a specific species of fish based on the location given by the user, so a Blue Groper would be considered “rare” in the U.S, while being common in Australia. For a certain amount of fish sightings, we offer rewards to nearby restaurants and shops in the form of a personalized QR Code. This specific QR code is on-time, and offers discounts of up to 20%. 

Alongside this, we offer a potential hardware prototype to assist users in searching for new populations of fish. This is in the form of a “buoy”, nearby buoy’s notify users if there are a large amount of fish in a given radius, checked by the cameras. This incentivises players to track buoy’s, and scan new populations of fish nearby.


## How we built ReefQuest
Utilizing open source fish identification datasets on kaggle, and public agencies that host large numbers of fish species (NOAA, etc.) We trained a classifier to identify a given species of fish based on an uploaded picture. We created 4 main sources: the database, the rewards system, the AI classifier, and the user interface. We used many different platforms, and we found that Flet was an effective hosting service to run our app on. SQLite helped us develop our backend and database scripts while we used multiple modules to code our frontend strategies. We would take the user’s pictures alongside potential location data to estimate the rarity of the person’s finding. We gauged this as the “proportion of species type expected compared to the amount of marine wildlife in that area”, and we would later give different categories based on the user’s image. 

## Quick CAD Overview
We developed a Hardware project idea that integrates our fish-detection code. We designed a prototype through CAD of a buoy, which is attached to a tower and has four cameras, which will run and use our fish detection to detect and gather information on fish. After gathering the data, it can be sent to scientists. You can check out the CAD for this model on our GitHub, where everything is stored. 



## Challenges we ran into
We ran into a variety of different challenges, including the implementation and the direction of our project. First, we had to decide how we would add CAD as a viable component, as the team realized that it could have great impact if added, after much brainstorming and debate, we decided on the buoy idea as it assists in the user’s ability to find schools of fish in given areas. Secondly, we had to figure out the best platform hosting service, as we realized our project had multiple components that simple platforms such as google colab couldn’t handle. Additionally, we had issues with compatibility and scalability, as the user interface caused us to troubleshoot and debug more than expected, leading us to not finish some parts of the rewards system and classification index.


## Accomplishments that we're proud of
Our team is happy that we are actually able to produce a working prototype of ReefQuest. The diverse expertise played a huge role in how we divided up the work and how we created a final product. We also gained experience in incorporating multiple features into one project idea, such as the upload mechanics, fish information database, and rewards system. The brainstorming session was one of our best parts, as it allowed us to think beyond what was required for one track, and to integrate parts of other tracks into our overall product.


## What we learned
The skills and repertoire of the team varied widely, while some specialized in CAD, others specialized in coding and presenting the pitch. The challenges of troubleshooting and debugging were one of the biggest hurdles in the final 3 hours of the hackathon, alongside making sure our demo was good with only 1 hour remaining. But we learned more about environmental concerns for aquatic and marine wildlife, as North Carolina strives for more sustainable practices to reintroduce some species back into the state. One of the most valuable things we learned during this competition is that environmental and aquatic innovations aren’t limited to ecosystem conservation and AI tracking models, they can have real effects on people and lead others to change their perspectives on the other 71% of the planet that isn’t land.


## What's next for ReefQuest
We plan to update and to include the final parts of our reward system such as the personalized QR code, discounts, and certificates of merit. Alongside this, classifying how rare a specific species of fish given the location is another potential application that would significantly help both national agencies and app engagement. 

##Citations
Kvalheim, L., Stensrud, E., Knutsen, H., Hyvärinen, O., & Eiler, A. (2024). Integration of citizen science and eDNA reveals novel ecological insights for marine fish conservation. Environmental DNA, 6, e584. https://doi.org/10.1002/edn3.584 

Paxton, A. B., et al. (2019). Artificial reefs facilitate tropical fish at their range edge. Communications Biology, 2(1). 
