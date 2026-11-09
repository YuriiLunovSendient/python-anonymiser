"""Word lists used by the rule-based name detector (EN-UK, EN-US, UK, RU).

These are deliberately plain Python sets: no model, no download. Extend them
freely; every entry must be lower-case.
"""

FIRST_NAMES_EN = set("""
james john robert michael william david richard joseph thomas charles christopher
daniel matthew anthony donald steven paul andrew joshua kenneth kevin brian george
timothy ronald edward jason jeffrey ryan jacob gary nicholas eric jonathan stephen
larry justin scott brandon benjamin samuel gregory alexander patrick raymond dennis
jerry tyler aaron jose adam nathan henry douglas zachary peter kyle noah ethan
jeremy walter christian keith roger terry austin sean gerald carl harold dylan
arthur lawrence jordan jesse bryan billy bruce gabriel joe logan albert willie
alan eugene russell vincent philip bobby johnny bradley oliver harry charlie leo
freddie alfie archie theo oscar jamie callum connor liam lewis owen rhys ewan
mary patricia jennifer linda elizabeth barbara susan jessica sarah karen lisa
nancy betty sandra margaret ashley kimberly emily donna michelle carol amanda
melissa deborah stephanie dorothy rebecca sharon laura cynthia amy kathleen
angela shirley brenda emma anna pamela nicole samantha katherine christine helen
debra rachel carolyn janet maria catherine heather diane olivia julie joyce
victoria virginia lauren kelly christina joan evelyn judith andrea hannah megan
cheryl jacqueline martha madison teresa gloria sara janice ann kathryn abigail
sophia frances isabella julia denise danielle marilyn beverly charlotte natalie
theresa diana brittany doris kayla alexis lori marie amelia isla ava mia ella
poppy sophie chloe lucy evie freya ruth alice judy jean grace amber ruby daisy
lily rose may june april will bill mark max frank ray jack
""".split())

# Ukrainian + Russian names in Cyrillic, plus common Latin transliterations.
FIRST_NAMES_UK = set("""
олександр андрій сергій володимир дмитро іван михайло олег юрій юрiй віктор
микола василь петро тарас богдан ярослав роман максим артем денис євген ігор
костянтин павло степан григорій федір антон назар остап святослав вадим віталій
руслан станіслав анатолій валентин леонід олексій кирило данило тимофій марко
матвій олена ольга наталія наталя тетяна ірина світлана юлія оксана катерина
марія анна ганна людмила галина надія вікторія анастасія софія дарина христина
мар'яна мар’яна марʼяна соломія зоряна ярина богдана лариса валентина тамара
алла інна віра любов євгенія олександра діана аліна поліна вероніка уляна злата
мирослава яна
""".split())

FIRST_NAMES_RU = set("""
александр алексей андрей сергей владимир дмитрий иван михаил олег юрий виктор
николай василий пётр петр павел роман максим артём артем денис евгений игорь
константин антон кирилл илья никита егор матвей тимофей фёдор федор григорий
степан станислав вадим виталий руслан анатолий валентин леонид борис глеб
ярослав святослав елена ольга наталья наталия татьяна ирина светлана юлия
оксана екатерина мария анна людмила галина надежда виктория анастасия софья
софия дарья кристина марина ксения полина вероника алина диана евгения
александра валентина тамара алла инна вера любовь елизавета ульяна яна милана
""".split())

FIRST_NAMES_TRANSLIT = set("""
oleksandr olexandr oleksii oleksiy andrii andriy andrey serhii serhiy sergey
sergei sergii volodymyr vladimir dmytro dmitry dmitriy mykhailo mikhail oleh
oleg yurii yuriy yuri yury viktor mykola nikolai nikolay vasyl vasily taras
bohdan yaroslav maksym maxim artem denys yevhen evgeny evgeniy ihor igor pavlo
pavel kostiantyn konstantin olena elena olga olha natalia natalya nataliia
tetiana tatiana tatyana iryna irina svitlana svetlana yulia yuliia oksana
kateryna ekaterina anastasia anastasiia sofia sofiia daryna darya daria alina
khrystyna kristina viktoriia viktoria halyna galina lyudmila liudmyla nadiia
""".split())

FIRST_NAMES = FIRST_NAMES_EN | FIRST_NAMES_UK | FIRST_NAMES_RU | FIRST_NAMES_TRANSLIT

# Names that are also ordinary words. They only count when a capitalised
# neighbour (likely a surname) is right next to them.
AMBIGUOUS_NAMES = set("""
will bill mark may june april rose grace hope faith joy ray dawn art max frank
rich sky summer amber ruby daisy lily jack penny august guy jean sue pat chase
drew hunter miles wade cliff glen dale rob holly iris jade ivy olive angel eve
віра любов надія роман вера любовь надежда слава лев
""".split())

# Capitalised words that must never be swallowed as a "surname" neighbour.
STOP_WORDS = set("""
the a an and or of to from in on at by for with is are was dear hello hi hey
regards thanks thank kind best sincerely yours subject date re fw fwd cc bcc
monday tuesday wednesday thursday friday saturday sunday january february march
april may june july august september october november december street st road rd
avenue ave lane ln drive dr city town county state country company ltd llc inc
plc mr mrs ms miss dr prof sir madam name email phone address password username
login user account card number total page invoice order
вул вулиця пров просп м г обл район буд кв шановний шановна дякую привіт
вітаю добрий день улица ул дом д кв уважаемый уважаемая спасибо привет здравствуйте
пароль логін логин адреса адрес телефон пошта почта ім'я имя прізвище фамилия
""".split())

HONORIFICS = set("""
mr mrs ms miss mx dr prof sir lady lord dame
пан пані пане панi г-н г-жа господин госпожа гражданин гражданка товариш
""".split())
