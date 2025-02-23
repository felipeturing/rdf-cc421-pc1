#!/usr/bin/env python
"""
film.py: a simple tool to manage your movies review
Simon Rozet, http://atonie.org/
    - manage directors and writers
    - manage actors
    - handle non IMDB uri
    - markdown support in comment
Requires download and import of Python imdb library from
https://imdbpy.github.io/ - (warning: installation
will trigger automatic installation of several other packages)
--
Usage:
    film.py whoami "John Doe <john@doe.org>"
        Initialize the store and set your name and email.
    film.py whoami
        Tell you who you are
    film.py http://www.imdb.com/title/tt0105236/
        Review the movie "Reservoir Dogs"
"""

import datetime
import os
import sys
import re
import time

try:
    import imdb
except ImportError:
    imdb = None

from rdflib import BNode, ConjunctiveGraph, URIRef, Literal, Namespace, RDF
from rdflib.namespace import FOAF, DC

storefn = os.path.expanduser("~/movies.n3")
# storefn = '/home/simon/codes/film.dev/movies.n3'
storeuri = "file://" + storefn
title = "Movies viewed by %s"

r_who = re.compile(
    r"^(.*?) <([a-z0-9_-]+(\.[a-z0-9_-]+)*@[a-z0-9_-]+(\.[a-z0-9_-]+)+)>$"
)

IMDB = Namespace("http://www.csd.abdn.ac.uk/~ggrimnes/dev/imdb/IMDB#")
REV = Namespace("http://purl.org/stuff/rev#")


class Store:
    def __init__(self):
        self.graph = ConjunctiveGraph()
        if os.path.exists(storefn):
            self.graph.load(storeuri, format="n3")
        self.graph.bind("dc", DC)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("imdb", IMDB)
        self.graph.bind("rev", "http://purl.org/stuff/rev#")

    def save(self):
        self.graph.serialize(storeuri, format="n3")

    def who(self, who=None):
        if who is not None:
            print("Bienvenido.\nSe creo tu archivo RDF en el formato N3 (Triples s+p+o)")
            name, email = (r_who.match(who).group(1),
                           r_who.match(who).group(2))
            self.graph.add(
                (URIRef(storeuri), DC["title"], Literal(title % name)))
            self.graph.add((URIRef(storeuri + "#author"),
                            RDF.type, FOAF["Person"]))
            self.graph.add((URIRef(storeuri + "#author"),
                            FOAF["name"], Literal(name)))
            self.graph.add((URIRef(storeuri + "#author"),
                            FOAF["mbox"], Literal(email)))
            self.save()
        else:
            print("Estas consultado quién eres.")
            print(list(self.graph.objects(
                URIRef(storeuri + "#author"), FOAF["name"])))
            return self.graph.objects(URIRef(storeuri + "#author"), FOAF["name"])

    def new_movie(self, movie):
        movieuri = URIRef("http://www.imdb.com/title/tt%s/" % movie.movieID)
        self.graph.add((movieuri, RDF.type, IMDB["Movie"]))
        self.graph.add((movieuri, DC["title"], Literal(movie["title"])))
        self.graph.add((movieuri, IMDB["year"], Literal(int(movie["year"]))))
        self.save()

    def new_review(self, movie, date, rating, comment=None):
        review = BNode()  # @@ humanize the identifier (something like #rev-$date)
        movieuri = URIRef("http://www.imdb.com/title/tt%s/" % movie.movieID)
        self.graph.add(
            (movieuri, REV["hasReview"], URIRef("%s#%s" % (storeuri, review)))
        )
        self.graph.add((review, RDF.type, REV["Review"]))
        self.graph.add((review, DC["date"], Literal(date)))
        self.graph.add((review, REV["maxRating"], Literal(5)))
        self.graph.add((review, REV["minRating"], Literal(0)))
        self.graph.add((review, REV["reviewer"], URIRef(storeuri + "#author")))
        self.graph.add((review, REV["rating"], Literal(rating)))
        if comment is not None:
            self.graph.add((review, REV["text"], Literal(comment)))
        self.save()

    def movie_is_in(self, uri):
        return (URIRef(uri), RDF.type, IMDB["Movie"]) in self.graph


def help():
    print(__doc__.split("--")[1])


def register_review(s:Store, movie_url ,default_values ):
    if s.movie_is_in(movie_url):
        print("Movie is in store")
        raise
    else:
        i = imdb.IMDb()
        movie = i.get_movie(
            movie_url[len("http://www.imdb.com/title/tt"): -1])
        print("%s (%s)" % (movie["title"].encode("utf-8"), movie["year"]))
        for director in movie["director"]:
            print("directed by: %s" % director["name"].encode("utf-8"))
        for writer in movie["writer"]:
            print("written by: %s" % writer["name"].encode("utf-8"))
        s.new_movie(movie)
        rating = None
        if default_values:
            rating = 4
            date = datetime.datetime(*time.strptime("2020-05-01", "%Y-%m-%d")[:6])
            comment = "Comentario por defecto"
        else:
            while not rating or (rating > 5 or rating <= 0):
                try:
                    rating = int(eval(input("Rating (on five): ")))
                except ValueError:
                    rating = None
            date = None
            while not date:
                try:
                    i = eval(input("Review date (YYYY-MM-DD): "))
                    date = datetime.datetime(*time.strptime(i, "%Y-%m-%d")[:6])
                except:
                    date = None
            comment = eval(input("Comment: "))
        s.new_review(movie, date, rating, comment)


def main(argv=None):
    if not argv:
        argv = sys.argv
    s = Store()
    if argv[1] in ("help", "--help", "h", "-h"):
        help()
    elif argv[1] == "whoami":
        if os.path.exists(storefn):
            print("Antes de ir a who")
            print(list(s.who())[0])
        else:
            s.who(argv[2])
    elif argv[1].startswith("http://www.imdb.com/title/tt"):
        if s.movie_is_in(argv[1]):
            print("Movie is in store")
            raise
        else:
            register_review(s , argv[1] )
    elif argv[1] == "autoload":
        if argv[2].endswith(".txt"):
            with open(argv[2]) as f:
                line = f.readline()
                while line:
                    parts = line.split(":")
                    id_number = parts[-1]
                    print("id :",  id_number)
                    print("parts : "  , parts)
                    register_review(s, "http://www.imdb.com/title/tt" +str(id_number).replace(" " , "")  , default_values = True)
                    line = f.readline()


    else:
        help()


if __name__ == "__main__":
    if not imdb:
        raise Exception(
            'This example requires the IMDB library! Install with "pip install imdbpy"'
        )
    main()
