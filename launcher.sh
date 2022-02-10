for website in\
 https://www.africanews.com\
 https://www.gov.za\
 https://www.camer-sport.com;
do
	./crawler.py $website -t 2 -s 1; # add & for parallel execution
done