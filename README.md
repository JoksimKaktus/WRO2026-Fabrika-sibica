Dokumentacija tima „Fabrika Šibica“

Ovaj robot je pravljen da se takmiči u kategoriji “Future Engineers” WRO 2026. Cilj je napraviti autonomno vozilo koje će samostalno moći da izbjegava i zaobilazi prepreke. 

Oprema

Imali smo relativno ograničenu opremu za korišćenje. Pod tim podrazumijevam da smo već imali „OVONIC 3S 2200mAh 50c“ baterije(i još po neke komponente, vidi se dalje u tekstu), i samim tim nismo razmišljali o drugom načinu napajanja. 

Kao mikrokontroler smo koristili Raspberry Pi 5. Na raspolaganju smo imali i Raspberry Pi 4, ali zbog boljih specifikacija i integrisanog hlađenja izabrali smo da koristimo Pi 5.

Postojao je izbor između kamera koje ćemo koristiti. Imali smo Raspberry Pi Camera Module v1 i Module v2. Prvi testovi su vršeni sa Module v1 kamerom i bili smo zadovoljni jasnoćom i kvalitetom slike. Zatim smo prešli na Module v2, i dobili smo drugačiju sliku. Bila je iz drugog fokusa i malo drugačijih boja. Da ne bi gubili vrijeme na podešavanje nove kamere, vratili smo se na korišćenje Module v1.

Takođe smo već imali TT DC motor i L298n drajver za njih te samim tim nismo uzimali druge u obzir.

Da bi mjerili udaljenost od zidova imali smo izbor između HC-SR04 Ultrasoničnih senzora i VL53L0X Time of Flight senzora. Iz pređašnjih iskustava smo znali da Ultrasonični senzori imaju problema sa odjecima od zidova i dobijanje pogrešnih podataka. Takođe potrebno im je da su pod pravim uglom u odnosu na zid od kojeg mjere. Zbog ovih slabosti izabrali smo da koristimo VL53L0X Time of Flight senzore, koji imaju veću rezoluciju od Ultrasoničnih i manje su osjetljivi na ugao objekta od kojeg mjere udaljenost.

Zbog korišćenja VL53L0X Time of Flight senzora, javio se novi problem. Svaki od njih koristi istu adresu(0x29) pri i2c komunikaciji. Zbog toga koristimo TCA9548A multiplekser. Njegova svrha je da poveže više senzora koji imaju istu adresu i da ih odvoji po kanalima kako bi mogle da se čitaju vrijednosti sa svih senzora neometano.

Za upravljanje smo imali izbor između MG995 i MG996R servo motora. Pri testiranju nam se pokazalo da je MG995 precizniji za upravljanje, i moguće je upravljanje u manjim rezolucijama i samim tim smo izabrali njega.

Za postizanje traženih napona koristili smo tri LM2596 obarača napona(Buck Converter). Oni su ograničeni na maksimalnu struju od 2A što nam odgovara za servo i DC motor. Jedini problem bi mogao predstavljati obarač napona koji se povezuje na Raspberry Pi 5, koji pri većim opterećenjima može da povuče i 5A. S obzirom na to da nije povezan na monitor u toku runde i da se u toku testiranja pokazalo da može nesmetano da radi sa navedenim obaračom napona, ostali smo pri njemu.

Koristimo i MPU6050 žiroskop kako bi mogli lakše da upravljamo robotom.

Takođe, još jedan bitan dio opreme koji smo koristili je diferencijal iz RC auta(Wltoys 12428 sa odnosom 1:12).

Koristimo i dvije LED diode pomoću kojih dobijamo signal kada je Raspberry potpuno upaljen i kada su senzori za udaljenost inicijalizovani.

Koristimo samo jedno dugme za pokretanje skripte, jer Raspberry Pi 5 ima svoje dugme za uključivanje i isključivanje.

Još jedan hardverski dio koji koristimo je 608RS ležaj, dva komada.

Povezivanje

Baterija koju koristimo je označena na kapacitet od 11.1V, ali kada je u potpunosti puna može blago prevazići 12.5V. Nama je potrebno da napajamo Raspberry, DC motor i servo sa baterije. Senzore za udaljenost, žiroskop i multiplekser možemo da napajamo direktno sa Raspberry-ja. Napajanje za Raspberry je 5V, a servo motor je takođe označen da bi mogao da prihvati napon od 5V(označen je na napone od 4.5V do 7V). Nije najbolja ideja povezati ih na isti konverter napona(Testirano :( ). Zato smo koristili tri konventera napona. Napon na Raspberry je 5V, na servo motoru je 7V i za DC motor je ostavljen napon od 9V. DC motor je takođe označen na gornji napon od 7V, ali njega moramo da povežemo preko L298n drajvera koji ima pad napona od otprilike 2V.

Servo motor i L298n drajver moraju da imaju zajedničku masu(Uzemljenje) sa Raspberry-jem. Bez toga može da dođe do nestabilnosti u držanju pozicije kod serva(interno poznato kao epilepsija) ili da DC motor ne dobija svoj signal.

Senzori za udaljenost, žiroskop i multiplekser mogu da rade i na 3.3V i 5V, ali zbog toga što su logički pinovi na Raspberry-ju označeni na 3.3V, taj pin smo koristili za njihovo napajanje. Jedno kratko vrijeme smo napajali multiplekser i žiroskop na 5V, ali zbog grešaka u čitanjima prešli smo na 3.3V.

Dvije LED diode su povezane uz pomoć otpornika, a za dugme je korišćen PullUP otpornik u kodu.

Konekcije na Raspberry-ju su sledeće:
Servo – GPIO 19
L298n ENA – GPIO 13
L298n IN1 – GPIO 6
L298n IN2 – GPIO 5
ToF Back – GPIO 25
ToF Left – GPIO 8
ToF Center – GPIO 7
ToF Right – GPIO 1
Dugme – GPIO 16
LED – GPIO 23

Konstrukcija

S obzirom da smo već izabrali šta koristimo, ostalo je da sve komponente spakujemo na jednu konstrukciju. Glavni cilj je da bude kraća od 30cm i uža od 20cm. Granica za visinu je 30cm ali ona nas nije zabrinjavala. Krenuli smo od prednjeg upravljanja. Ono se satoji od dva prednja točka, dva ležaja da bi bio manji otpor okretanja točkova, servo motora i 3D konstrukcije koju smo napravili da sve to drži zajedno.

Da bi nam računica za skretanje bila jednostavnija, centar okretanja serva i točka su imali polugu do iste udaljenosti i time spojeni na zajedničku „letvu volana“. Ovim smo postigli da nam je jednak ugao serva i oba točka u svakom trenutku.

Jedna od korisnih stvari koju smo napravili je konektor za točak i ležaj. Oni su morali da budu takvih tolerancija da ne mogu sami da ispadnu ako bi se robot nagnuo. Isto takvo nalijeganje koristimo u dijelu koji povezuje ležaj sa osovinom i nošenjem. 

Na toj osnovi je povezan i servo motor, između točkova.

Iznad serva i točkova je konstrukcija koja drži senzore za udaljenost. Imali smo dva modela te konstrukcije. Jedna je imala servo naprijed i dva pod uglom od 25 stepeni naprijed u odnosu na zidove sa strana. Druga opcija je imala bočne senzore pod pravim uglom u odnosu na bočne zidove. Pri testiranju nam se pokazalo da senzori daju preciznije i konstantnije vrijednosti kada koriste konstrukciju koja drži senzore pod pravim uglom u odnosu na zidove, i samim tim smo izabrali nju da koristimo.

Iznad konstrukcije za senzore je ostavljeno mjesta da se poveže držač kamere. Centar kamere je na visini od 11.5cm i kamera je nagnuta naprijed pod uglom od 15 stepeni. Time smo dobili sliku kojom možemo jasno da vidimo objekte i linije za skretanje.

Zatim smo napravili držač za bateriju. Ideja kod držača za bateriju je bila da zauzima što manje prostora, a da nije teško izvaditi je i zamijeniti je sa novom. To smo riješili tako što smo napravili kućište dimenzija malo veće od dimenzija baterije, ostavili smo osigurač na jednom kraju u obliku slova T. Time pri zamjeni baterije treba samo izvući osigurač, zamijeniti baterije i vratiti ga.

Dizajniran je i nosač Raspberry-ja koji ne koristi navoje nego ima izbočine cilindričnog oblika koje su manje od njegovih rupa za navoje, i samim tim samo naliježe na njega.

Napravljen je i držač za L298n drajver koji ga drži samo na dva navoja jer se to ispostavilo kao dovoljno.

Osnova na koju je sve povezano je imala opciju da bude izrezana iz pleksiglasa ili da se 3D štampa. Zbog brzine za promjenu i integraciju novih djelova na druge pozicije izabrali smo da je 3D štampamo. Na prednjoj osnovi je zakačeno čitavo prednje vješanje, držači senzora udaljenosti i kamere,držač baterije kao i držač Raspberry-ja i drajvera.

Najviše problema smo imali oko zadnjeg diferencijala. Prva opcija je bila da se štampa, ali zbog krtosti plastike smo odlučili da koristimo metalni diferencijal. Izabrali smo Wltoys 12428, koji je imao promjer koji nam je odgovarao, i imao je malu unutrašnju otpornost na okretanje, za razliku od nekih drugih sličnih što smo isprobavali. 

Kada smo odlučili koji ćemo diferencijal da koristimo, ostalo nam je da napravimo kućište za njega, i način da povežemo DC motor sa njim. Našli smo model na internetu za naš diferencijal i prepravili ga da nam odgovara za naše kačenje sa zadnjom osnovom i motorom.

Zadnju osnovu smo napravili tako da se naprijed kači na držač baterije, a da ima izdignuti nosač DC motora i diferencijala, kako bi nam robot bio horizontalan. 

Napravljene su osovine koje se na jednu stranu povezuju sa diferencijalom, a na drugu stranu sa zadnjim točkovima. One se oslanjaju na oslonce koji se kače na zadnju osnovu.



Video:
https://youtube.com/shorts/3pL9WalHYMo?si=7q0_cxRy45ui33ve
