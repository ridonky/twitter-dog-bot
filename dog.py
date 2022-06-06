import re
import requests
import shutil

#dog() is main function for handling user input dog breed, and returns a validated dog breed to application.py with help of breed_list() and breed_handle()
def dog(dog_breed):
    dog_breed = str(dog_breed.lower().strip())
    breed_map = breed_list()
    dog_breed_handled = breed_handle(dog_breed, breed_map)
    print(dog_breed_handled)
    return dog_breed_handled

def breed_list():
    breeds = requests.get('https://dog.ceo/api/breeds/list/all').json()
    # make a key value pair of original breeds + transformed breeds
    breed_map = {}   
    for breed in breeds['message']:
        sub_breed = breeds['message'][breed]
        if len(sub_breed) == 0:
            breed_map[breed] = breed
        for sub in sub_breed:
            breed_transform = (sub + ' ' + breed)  
            breed_map[breed_transform] = breed     
    return breed_map

def breed_handle(dog_breed, breed_map):
    breed_handled = []
    for breed in breed_map:
        if dog_breed == breed:
            breed_handled.append(breed)
            return breed_handled
    for breed in breed_map:
        if dog_breed in breed:
            if breed not in breed_handled:
                breed_handled.append(breed)
        elif re.search(' ', dog_breed): #handle 2 word dog names
            dog_breed_components = dog_breed.split()
            if re.search(dog_breed_components[0]+'.*'+dog_breed_components[1], breed) or re.search(dog_breed_components[1]+'.*'+dog_breed_components[0], breed):
                if breed not in breed_handled:
                    breed_handled.append(breed)
    #test partial match, returning multiple breed options
    for breed in breed_map:
        if re.search(' ', breed):
            breed_map_components = breed.split() 
            #handle just 1 word of 2 word name matching map, or matching multiple shits in the map
            if re.search(dog_breed, breed_map_components[0]) or re.search(dog_breed, breed_map_components[1]):
                if breed not in breed_handled:
                    breed_handled.append(breed)
    if breed_handled == []:
            breed_handled.append('all')        
    return breed_handled


#pic_file() is the main function for returning a dog pic for application.py, with help of breed_list(), breed_pic_url()
def pic_file(dog_breed):
    breed_map = breed_list()
    pic_file = breed_pic_url(dog_breed, breed_map)
    return pic_file

def breed_pic_url(dog_breed_handled, breed_map):
    for breed in breed_map:
        if dog_breed_handled == 'all':
            dog_pic = requests.get('https://dog.ceo/api/breeds/image/random').json()        
        elif dog_breed_handled == breed:
        # if the key and value are the same, u good    
            if breed == breed_map[breed]:
                breed_url = ('https://dog.ceo/api/breed/' + breed + '/images/random')
            else:
                compound_breed = breed_map[breed].split()
                breed_url = ('https://dog.ceo/api/breed/' + compound_breed[1] + '/' + compound_breed[0] + '/images/random')
            dog_pic = requests.get(breed_url).json()        
    dog_pic = dog_pic['message']   
    filename = dog_pic.split("/")[-1]
    r = requests.get(dog_pic, stream=True)
    if r.status_code == 200:
        r.raw.decode_content = True
        with open(filename,'wb') as f:
            shutil.copyfileobj(r.raw,f)
        return filename