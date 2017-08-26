#-*- coding:utf-8 -*-
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.garden.mapview import MapView, MapMarker, MapLayer, MarkerMapLayer
from kivy.uix.image import Image, AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import mainthread
from kivy.utils import get_color_from_hex as rgb
from kivy.graphics import *
from kivy.factory import Factory
from kivy.core.window import Window
from geopy.distance import vincenty
from plyer import gps

import requests, json
import platform
import time, threading

#CODE BELOW
Window.clearcolor = (1, 1, 1, 1)
class Veterinaria:
    pass
#exibe uma tela de carregando com uma mensagem fofa
class TelaCarrega(Popup):
    title='Carregando'
    def __init__(self, **kwargs):
        super(TelaCarrega, self).__init__(**kwargs)
        self.content=Image(source='loading.png')

#lista com um item pra cada veterinária perto
class ListaVet(StackLayout):
    orientation='tb-lr'
    lat=0
    lon=0
    spacing=[0, .5]

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def show_popup(self):
        self.pop_up = Factory.TelaCarrega()
        self.pop_up.open()

    def tempo_espera(self):
        estetempo = time.time()
        while self.esperando:
            time.sleep(1)
        self.pop_up.dismiss()

    @mainthread
    def on_location(self, **kwargs):
        distancia = vincenty( (kwargs['lat'], kwargs['lon']),
                              (self.lat, self.lon) ).meters
        if distancia > 100:
            engine = Engine()
            self.lat=kwargs['lat']
            self.lon=kwargs['lon']
            self.dados = engine.requerir_dados(self.lat, self.lon)
            for linha in self.dados:
                self.height += 80
                self.add_widget(ItemVet(dados=engine.buscar_detalhes(linha['place_id'])))
            self.esperando=False


    def __init__(self, **kwargs):
        super(ListaVet, self).__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)

            self.rect = Rectangle(pos=self.center, size=(self.width/2,
                                                         self.height/2))
        self.bind(pos=self.update_rect,size=self.update_rect)

        self.esperando = True
        meufio = threading.Thread(target=self.tempo_espera)
        meufio.start()
        self.show_popup()
        try:
            gps.configure(on_location = self.on_location)
        except NotImplementedError:
            print('não conectou')
        gps.start(1000, 0)

        #dados = self.requerir_dados(self.lat, self.lon)

        self.size_hint = (1., None)
        self.height = 80
        self.add_widget(Label(size_hint=(1., None), height=80))


#item de veterinária que fica na lista :p
class ItemVet(BoxLayout):
    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            engine = Engine()
            raiz = self.get_root_window()
            #raiz.add_widget(JanelaVet(place_id=self.place_id))
            raiz.add_widget(JanelaVet(dados=self.dados))

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def __init__(self, **kwargs):
        super(ItemVet, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0.14901960784313725, 0.807843137254902, 0.8509803921568627, 1)

            self.rect = Rectangle(pos=self.center, size=(self.width/2,
                                                         self.height/2))
        self.bind(pos=self.update_rect,size=self.update_rect)
        self.dados = kwargs['dados']
        #self.nome = dados['name']
        #self.rating = dados['rating']
        #self.telefone = dados['formatted_phone_number']
        #self.endereco = dados['formatted_address']
        #self.icone = dados['icon']
        self.size_hint = (1., None)
        self.height = 80


        #self.add_widget(AsyncImage(source=self.dados['icon']))
        engine=Engine()
        if 'rating' in self.dados:
            self.add_widget( Image(source = engine.avaliar(rank = self.dados['rating'])) )
        else:
            self.add_widget( Image(source = engine.avaliar(rank = 0)) )
        print(self.dados.keys())
        self.add_widget(Label(text=self.dados['name'].encode('utf-8').strip(),
                        text_size=(self.width * 3, None)))


#Layout que carrega mapa ou lista
class Layout_Pagina(RelativeLayout):
    def show_popup(self):
        self.pop_up = Factory.TelaCarrega()
        self.pop_up.open()

    def tempo_espera(self):
        estetempo = time.time()
        while self.esperando:
            time.sleep(1)
        self.pop_up.dismiss()

    def close(self, *args):
        gps.stop()
        app = App.get_running_app()
        app.root.remove_widget(self)

    def __init__(self, **kwargs):
        super(Layout_Pagina, self).__init__(**kwargs)
        root = self.get_parent_window()
        #######

        #######



        if kwargs['parametro'] == 'mapa':
            self.esperando = True
            self.show_popup()
            meufio = threading.Thread(target=self.tempo_espera)
            meufio.start()
            self.add_widget(MapaCidade())
            self.esperando=False
        elif kwargs['parametro'] == 'lista':
            self.content = ListaVet()
            self.content.bind(minimum_height=self.content.setter('height'))
            self.scrollview = ScrollView(size_hint=(1, 1))
            self.scrollview.do_scroll_x = False
            self.scrollview.add_widget(self.content)
            self.add_widget(self.scrollview)
            self.esperando=False
        self.add_widget(Button(size_hint=(.2, .08), pos_hint={'x':0, 'y':.92},
                text='VOLTAR', on_release=self.close))

#janelinha na frente do mapa com as informações da veterinária clicada
#note que ao clicar no mapa a janela some
class JanelaVet(BoxLayout):
    orientation='vertical'

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            raiz = self.get_root_window()
            raiz.remove_widget(self)

    def __init__(self,  **kwargs):
        super(JanelaVet, self).__init__(**kwargs)
        with self.canvas:
            Color(0.0, 0.4980392156862745, 0.5333333333333333, 1)
            self.rect = Rectangle(pos=self.center, size=(self.width/2,
                                                         self.height/2))

        self.bind(pos=self.update_rect,size=self.update_rect)
        self.size_hint=(.8, .6)
        self.pos_hint={'center_x':.5, 'center_y':.5}
        engine = Engine()
        #dados = self.buscar_detalhes(kwargs['place_id'])
        dados=kwargs['dados']
        self.add_widget(Label(font_size=24, text=dados['name'].encode('utf-8').strip()))
        #self.add_widget(Label(font_size=24, text=str(dados['rating']), size_hint_y=.05))
        self.add_widget( Image(source = engine.avaliar(rank = dados['rating'])) )
        self.add_widget(Label(font_size=24, text=dados['formatted_phone_number'].encode('utf-8').strip()))
        self.add_widget(Label(font_size=24, text=dados['formatted_address'].encode('utf-8').strip(),
                                text_size=(self.width * 3, None)))

#a marcação no mapa que representa uma veterinária
class VeteriMarca(MapMarker):
    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            engine = Engine()
            raiz = self.get_root_window()
            #raiz.add_widget(JanelaVet(place_id=self.place_id))
            raiz.add_widget(JanelaVet(dados=engine.buscar_detalhes(self.place_id)))

    def __init__(self,  **kwargs):
        super(VeteriMarca, self).__init__(**kwargs)
        self.place_id = kwargs['place_id']

#por enquanto só faz o request
#não estou certo do que fazer com essa classe
class Engine():
    def __init__(self):
        self.file = open('key.ini', 'r')
        self.chave = self.file.read().split('\n')

    def avaliar(self, **kwargs):
        if kwargs['rank'] == 0:
            return ''
        elif 0 < kwargs['rank'] < 1:
            return 'rating/meio.png'
        elif kwargs['rank'] == 1:
            return 'rating/1.png'
        elif 1 < kwargs['rank'] < 2:
            return 'rating/1_meio.png'
        elif kwargs['rank'] == 2:
            return 'rating/2.png'
        elif 2 < kwargs['rank'] < 3:
            return 'rating/2_meio.png'
        elif kwargs['rank'] == 3:
            return 'rating/3.png'
        elif 3 < kwargs['rank'] < 4:
            return 'rating/3_meio'
        elif kwargs['rank'] == 4:
            return 'rating/4.png'
        elif 4 < kwargs['rank'] < 5:
            return 'rating/4_meio.png'
        elif kwargs['rank'] == 5:
            return 'rating/5.png'

    def requerir_dados(self, lat, lon):
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={!s},{!s}&radius=5000&type=veterinary_care&key={!s}".format(str(lat), str(lon), self.chave[0])
        resposta = requests.get(url)
        dados = json.loads(resposta.text)
        return dados['results']

    def buscar_detalhes(self, place_id):
        url ='https://maps.googleapis.com/maps/api/place/details/json?placeid={!s}&key={!s}'.format(str(place_id), self.chave[0])
        texto = requests.get(url)
        dados = json.loads(texto.text)
        return(dados['result'])

#mapa com as veterinárias num raio de 5 km
class MapaCidade(MapView):
    minha_pos = MapMarker(lat=0, lon=0, source='minha_pos.png')

    @mainthread
    def on_location(self, **kwargs):
        distancia = vincenty( (kwargs['lat'], kwargs['lon']),
                              (self.minha_pos.lat, self.minha_pos.lon) ).meters
        if distancia > 100:
            self.lat=kwargs['lat']
            self.lon=kwargs['lon']
            self.center_on(kwargs['lat'], kwargs['lon'])
            self.adicionar_marcas(self.engine.requerir_dados(self.lat, self.lon ))
            self.minha_pos.lat=self.lat
            self.minha_pos.lon=self.lon

    def adicionar_marcas(self, dados, camada=None):
        for linha in dados:
            self.add_marker(VeteriMarca(lat=linha['geometry']['location']['lat'],
                                      lon=linha['geometry']['location']['lng'],
                                      place_id=linha['place_id'],
                                      source='mini_icon.png'))

    def __init__(self, **kwargs):
        super(MapaCidade, self).__init__(**kwargs)
        self.engine = Engine()
        try:
            gps.configure(on_location=self.on_location)
        except NotImplementedError:
            print('error')
        gps.start(1000, 0)
        self.add_widget(self.minha_pos)
        self.zoom=14


#widget raiz com algumas coisas
class Raiz(FloatLayout):

    def close(self, *args):
        self.remove_widget(self.leiaute)

    def abre_lista(self, *args):
        self.leiaute = Layout_Pagina(parametro='lista')
        self.add_widget(self.leiaute)
    def abre_mapa(self, *args):
        self.leiaute = Layout_Pagina(parametro='mapa')
        self.add_widget(self.leiaute)


    def __init__(self, **kwargs):
        super(Raiz, self).__init__(**kwargs)

        self.add_widget(Button(size_hint=(.2, .1), pos_hint={'x':0, 'y':.9},
                text='MAPA', on_release=self.abre_mapa))

        self.add_widget(Button(size_hint=(.2, .1), pos_hint={'x':0, 'y':.8},
                text='LISTA', on_release=self.abre_lista))
#Classe do app :)
class IVetApp(App):
    def build(self):
        return Raiz()

#só pretendo fazer um arquivo .py pra esse app
if __name__ == '__main__':
    IVetApp().run()
