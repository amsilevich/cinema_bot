def clip_link(link):
    protocols = ['https', 'http']
    for protocol in protocols:
        if link.startswith(protocol):
            pure_link = link[len(protocol) + len('://'):]
            return pure_link[:pure_link.find('/')]
