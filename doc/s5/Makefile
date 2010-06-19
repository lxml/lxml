
SLIDES=$(subst .txt,.html,$(wildcard *.txt))

slides: $(SLIDES)

%.html: %.txt
	python rst2s5.py --current-slide --language=en $< $@

clean:
	rm -f *~ $(SLIDES)
