/* =============================================================
   Hindi / English switching.
   Every translatable string lives here, in both languages.
   Markup carries the key:
     data-i18n       -> textContent
     data-i18n-html  -> innerHTML (for strings containing <strong>, <br>, links)
     data-i18n-ph    -> placeholder
     data-i18n-aria  -> aria-label
     data-i18n-title -> title
   English is also written into index.html, so the page still reads
   correctly if this script fails to load.
   ============================================================= */

var I18N = {

  en: {
    'html.title'   : 'Dr. Om Prakash Gupta — Senior Advocate, Kanpur Nagar Court',
    'lang.en'      : 'English',
    'lang.hi'      : 'हिन्दी',
    'lang.switch'  : 'Choose language',

    'gate.title'   : 'Disclaimer',
    'gate.p'       : 'As per the rules of the Bar Council of India, an advocate is not permitted to solicit work or advertise. By clicking &ldquo;I Agree&rdquo; you acknowledge that:',
    'gate.li1'     : 'there has been no advertisement, solicitation, invitation or inducement of any sort from the advocate or the chamber;',
    'gate.li2'     : 'you wish to gain information about the advocate for your own information and use;',
    'gate.li3'     : 'all information on this site is provided on your specific request and entirely at your own volition;',
    'gate.li4'     : 'nothing here constitutes legal advice, and no advocate–client relationship is created by your use of this site.',
    'gate.agree'   : 'I Agree',
    'gate.no'      : 'I Do Not Agree',

    'nav.about'    : 'About',
    'nav.practice' : 'Practice',
    'nav.process'  : 'Process',
    'nav.appt'     : 'Appointment',
    'nav.contact'  : 'Contact',
    'nav.cta'      : 'Book Appointment',
    'brand.sub'    : 'Senior Advocate & Associates',
    'nav.open'     : 'Open menu',
    'nav.close'    : 'Close menu',

    'hero.kicker'  : 'Kanpur Nagar Court &bull; Chamber No. 1',
    'hero.name'    : 'Dr. Om Prakash Gupta',
    'hero.role'    : 'Senior Advocate',
    'hero.lead'    : '<strong>Over 47 years</strong> in legal consultation and courtroom practice &mdash; advising and representing clients in civil, criminal, property, revenue, family and service matters before the courts at Kanpur Nagar.',
    'hero.cta1'    : 'Book an Appointment',
    'hero.cta2'    : 'Call +91 94501 32436',
    'hero.cardcap' : 'Visiting card &mdash; tap to view full size',
    'hero.cardtitle': 'Open the visiting card full size',

    'ledger.1'     : 'Years of practice',
    'ledger.2'     : 'Areas of law',
    'ledger.3v'    : 'No.&nbsp;1',
    'ledger.3'     : 'Chamber, Kanpur Nagar Court',
    'ledger.4'     : 'Languages — Hindi & English',

    'about.kicker' : 'About the Advocate',
    'about.h2'     : 'Nearly five decades at the bar,<br>one standard of counsel.',
    'about.p1'     : 'Dr. Om Prakash Gupta is a Senior Advocate with more than forty-seven years of continuous practice. His chamber &mdash; <strong>Genius Senior Advocate &amp; Associates, Chamber No. 1 at the Kanpur Nagar Court</strong> &mdash; advises individuals, families, landholders, employees, traders and small businesses, and appears for them at every stage: from the first notice through trial, appeal and revision.',
    'about.p2'     : 'The chamber&rsquo;s approach is deliberately plain. An honest reading of the case at the first meeting. A realistic view of time and cost. Documentation prepared carefully enough that it holds up years later. Clients are told what the law permits, not what they would prefer to hear.',
    'about.t1'     : 'Practice before the District &amp; Sessions Court and subordinate courts at Kanpur Nagar',
    'about.t2'     : 'Appearances before tribunals, revenue authorities and consumer commissions',
    'about.t3'     : 'Drafting, vetting and registration of deeds, agreements and settlements',
    'about.t4'     : 'Consultation in Hindi and English',
    'about.caption': 'At the court premises',

    'pr.kicker'    : 'Practice Areas',
    'pr.h2'        : 'Matters the chamber handles',
    'pr.sub'       : 'If your matter is not listed here, please still ask. The chamber will tell you frankly whether it is the right place for it.',
    'pr.1h':'Civil Litigation',   'pr.1p':'Suits for declaration, possession, injunction, specific performance, partition, recovery and damages; appeals and revisions.',
    'pr.2h':'Criminal Law',       'pr.2p':'Bail and anticipatory bail, quashing petitions, trial defence, complaints, appeals and revisions.',
    'pr.3h':'Property &amp; Land','pr.3p':'Title examination, sale, gift and partition deeds, mutation, boundary and possession disputes, builder disputes.',
    'pr.4h':'Revenue &amp; Tenancy','pr.4p':'Proceedings before the Tehsildar, SDM and Commissioner; land records, varasat, chakbandi and revenue appeals.',
    'pr.5h':'Family &amp; Matrimonial','pr.5p':'Divorce, restitution, maintenance, custody and guardianship, domestic violence proceedings, mutual settlements.',
    'pr.6h':'Service &amp; Labour','pr.6p':'Departmental enquiries, termination and suspension, promotion and seniority, pension and retiral dues, labour disputes.',
    'pr.7h':'Writs &amp; Constitutional','pr.7p':'Writ petitions under Article 226 against State action, public authorities and statutory bodies; contempt proceedings.',
    'pr.8h':'Cheque Bounce &amp; Recovery','pr.8p':'Complaints under Section 138 of the Negotiable Instruments Act, legal notices, money suits and execution.',
    'pr.9h':'Motor Accident Claims','pr.9p':'Compensation claims before the MACT, insurance disputes and appeals against inadequate awards.',
    'pr.10h':'Consumer Protection','pr.10p':'Complaints before the District, State and National Commissions for deficiency in service and unfair trade practice.',
    'pr.11h':'Succession &amp; Wills','pr.11p':'Wills, succession certificates, probate and letters of administration, family settlements and inheritance disputes.',
    'pr.12h':'Agreements &amp; Drafting','pr.12p':'Drafting and vetting of agreements, power of attorney, lease and rent deeds, notices, affidavits and undertakings.',

    'ps.kicker'    : 'How It Works',
    'ps.h2'        : 'From your first call to your first hearing',
    'ps.1h':'Request an appointment','ps.1p':'Fill the form below or call the chamber. Mention your city and the nature of the dispute in a line or two.',
    'ps.2h':'Confirmation','ps.2p':'The chamber confirms your slot on WhatsApp or by phone, and tells you which papers to bring.',
    'ps.3h':'Consultation','ps.3p':'Your papers are read, the position in law is explained, and the realistic options, timeline and cost are set out.',
    'ps.4h':'Representation','ps.4p':'If you decide to proceed, drafting begins, the matter is filed, and you are kept informed at every date.',

    'ap.kicker'    : 'Appointment',
    'ap.h2'        : 'Book a consultation',
    'ap.p'         : 'Complete the form and your request goes straight to the chamber on WhatsApp &mdash; or by email, if you prefer. You will receive confirmation of the date and time before the meeting.',
    'ap.t1'        : 'Chamber sittings <strong>Monday to Saturday</strong>; Sunday and court holidays closed',
    'ap.t2'        : 'Telephone and video consultation for outstation clients',
    'ap.t3'        : 'Please carry all original documents and any notice or order received',
    'ap.t4'        : 'Your details are used only to arrange and conduct the consultation',
    'ap.call'      : 'Call the chamber',
    'ap.wa'        : 'WhatsApp',

    'f.name':'Full name','f.name.ph':'Your full name',
    'f.phone':'Mobile number','f.phone.ph':'10-digit mobile number',
    'f.email':'Email','f.email.opt':'(optional)','f.email.ph':'name@example.com',
    'f.city':'City / District','f.city.ph':'e.g. Kanpur Nagar',
    'f.mode':'Mode of consultation','f.mode.1':'In chamber','f.mode.2':'Telephone','f.mode.3':'Video call',
    'f.matter':'Nature of matter','f.select':'Please select',
    'f.m1':'Civil suit / property dispute','f.m2':'Criminal matter / bail','f.m3':'Revenue or land record matter',
    'f.m4':'Family or matrimonial matter','f.m5':'Service or labour matter','f.m6':'Writ petition',
    'f.m7':'Cheque bounce / money recovery','f.m8':'Motor accident claim','f.m9':'Consumer complaint',
    'f.m10':'Succession, will or probate','f.m11':'Drafting or documentation','f.m12':'Other / not sure',
    'f.date':'Preferred date','f.time':'Preferred time','f.t6':'Any time &mdash; chamber may decide',
    'f.brief':'Brief description of your matter','f.brief.ph':'In two or three lines: what happened, when, and what stage the matter is at.',
    'f.consent':'I understand that submitting this form does not create an advocate&ndash;client relationship, and that no legal advice is given until the consultation takes place.',
    'f.sendwa':'Send request on WhatsApp','f.sendmail':'Send request by email instead',
    'f.note':'<strong>Please note:</strong> if you send your details by <strong>email</strong>, kindly also inform the chamber on a <a href="tel:+919450132436">phone call</a> for the same, so that your message is not missed.',

    'pay.kicker':'Consultation Fee','pay.h3':'Payment by UPI',
    'pay.p':'Scan the code with any UPI application &mdash; Google&nbsp;Pay, PhonePe, Paytm, BHIM or your bank&rsquo;s own app &mdash; to pay the consultation fee.',
    'pay.id':'UPI ID',
    'pay.warn':'Please confirm the amount with the chamber by phone before paying, and keep the transaction reference. The chamber never asks for an OTP, a PIN or card details &mdash; if anyone does, it is not us.',

    'ct.kicker':'Contact','ct.h2':'Chamber &amp; contact details',
    'ct.ch':'Chamber',
    'ct.cp':'<strong>Genius Senior Advocate &amp; Associates</strong><br><strong>Chamber No. 1</strong><br>Kanpur Nagar Court<br>District &amp; Sessions Court campus, Kanpur Nagar',
    'ct.ph':'Telephone','ct.wa':'Message on WhatsApp',
    'ct.em':'Email','ct.emnote':'After emailing your details, please also inform the chamber on a phone call for the same.',
    'ct.hr':'Chamber hours','ct.hrp':'Monday &ndash; Saturday<br>Morning and evening sittings by appointment<br>Sunday and court holidays: closed',

    'ft.name':'Dr. Om Prakash Gupta &mdash; Senior Advocate',
    'ft.sub':'Genius Senior Advocate &amp; Associates &bull; Chamber No. 1, Kanpur Nagar Court',
    'ft.legal':'The contents of this website are for general information only and do not constitute legal advice. No advocate&ndash;client relationship is created by accessing this website or by sending an appointment request. In accordance with the rules of the Bar Council of India, this website is not an advertisement or a solicitation of work.',
    'ft.copy':'Genius Senior Advocate &amp; Associates.',
    'fab.call':'Call the chamber','fab.wa':'Message the chamber on WhatsApp',

    'err.name'   : 'Please enter your full name.',
    'err.phone'  : 'Please enter a valid 10-digit Indian mobile number.',
    'err.email'  : 'Please enter a valid email address, or leave it blank.',
    'err.matter' : 'Please select the nature of your matter.',
    'err.time'   : 'Please choose a preferred time.',
    'err.date'   : 'Please choose a preferred date.',
    'err.past'   : 'Please choose a date from tomorrow onwards.',
    'err.sunday' : 'The chamber is closed on Sunday. Please choose another day.',
    'err.consent': 'Please acknowledge the note above to continue.',
    'st.wa'      : 'WhatsApp has been opened with your request. Please press send there to deliver it to the chamber.',
    'st.mail'    : 'Your email application has been opened with the request filled in. Please press send there.',

    'msg.title':'Appointment request','msg.name':'Name','msg.mobile':'Mobile','msg.email':'Email',
    'msg.city':'City / District','msg.mode':'Mode','msg.matter':'Nature of matter',
    'msg.date':'Preferred date','msg.time':'Preferred time','msg.brief':'Brief',
    'msg.from':'Sent from the chamber website.','msg.locale':'en-IN'
  },

  hi: {
    'html.title'   : 'डॉ. ओम प्रकाश गुप्ता — वरिष्ठ अधिवक्ता, कानपुर नगर न्यायालय',
    'lang.en'      : 'English',
    'lang.hi'      : 'हिन्दी',
    'lang.switch'  : 'भाषा चुनें',

    'gate.title'   : 'अस्वीकरण',
    'gate.p'       : 'भारतीय विधिज्ञ परिषद के नियमों के अनुसार अधिवक्ता को कार्य की याचना अथवा विज्ञापन करने की अनुमति नहीं है। &ldquo;मैं सहमत हूँ&rdquo; पर क्लिक करके आप स्वीकार करते हैं कि:',
    'gate.li1'     : 'अधिवक्ता अथवा चैम्बर की ओर से किसी प्रकार का विज्ञापन, याचना, आमंत्रण या प्रलोभन नहीं दिया गया है;',
    'gate.li2'     : 'आप अपनी जानकारी एवं उपयोग हेतु अधिवक्ता के विषय में सूचना प्राप्त करना चाहते हैं;',
    'gate.li3'     : 'इस साइट की समस्त जानकारी आपके विशेष अनुरोध पर तथा पूर्णतः आपकी स्वेच्छा से प्राप्त की जा रही है;',
    'gate.li4'     : 'यहाँ दी गई कोई भी बात विधिक परामर्श नहीं है, तथा इस साइट के उपयोग से अधिवक्ता–पक्षकार संबंध स्थापित नहीं होता।',
    'gate.agree'   : 'मैं सहमत हूँ',
    'gate.no'      : 'मैं सहमत नहीं हूँ',

    'nav.about'    : 'परिचय',
    'nav.practice' : 'कार्यक्षेत्र',
    'nav.process'  : 'प्रक्रिया',
    'nav.appt'     : 'अपॉइंटमेंट',
    'nav.contact'  : 'संपर्क',
    'nav.cta'      : 'अपॉइंटमेंट बुक करें',
    'brand.sub'    : 'सीनियर एडवोकेट एंड एसोसिएट्स',
    'nav.open'     : 'मेन्यू खोलें',
    'nav.close'    : 'मेन्यू बंद करें',

    'hero.kicker'  : 'कानपुर नगर न्यायालय &bull; चैम्बर नं. 1',
    'hero.name'    : 'डॉ. ओम प्रकाश गुप्ता',
    'hero.role'    : 'वरिष्ठ अधिवक्ता',
    'hero.lead'    : '<strong>47 वर्षों से अधिक</strong> का विधिक परामर्श एवं न्यायालय में पैरवी का अनुभव &mdash; कानपुर नगर के न्यायालयों में सिविल, आपराधिक, संपत्ति, राजस्व, पारिवारिक एवं सेवा संबंधी मामलों में परामर्श एवं पैरवी।',
    'hero.cta1'    : 'अपॉइंटमेंट बुक करें',
    'hero.cta2'    : 'कॉल करें: +91 94501 32436',
    'hero.cardcap' : 'विज़िटिंग कार्ड &mdash; पूरा देखने हेतु टैप करें',
    'hero.cardtitle': 'विज़िटिंग कार्ड पूरे आकार में देखें',

    'ledger.1'     : 'वर्षों का अनुभव',
    'ledger.2'     : 'विधि के क्षेत्र',
    'ledger.3v'    : 'नं.&nbsp;1',
    'ledger.3'     : 'चैम्बर, कानपुर नगर न्यायालय',
    'ledger.4'     : 'भाषाएँ — हिन्दी एवं अंग्रेज़ी',

    'about.kicker' : 'अधिवक्ता के विषय में',
    'about.h2'     : 'लगभग पाँच दशक का अनुभव,<br>परामर्श का एक ही स्तर।',
    'about.p1'     : 'डॉ. ओम प्रकाश गुप्ता वरिष्ठ अधिवक्ता हैं, जिन्हें सैंतालीस वर्षों से अधिक की निरंतर वकालत का अनुभव है। उनका चैम्बर &mdash; <strong>जीनियस सीनियर एडवोकेट एंड एसोसिएट्स, चैम्बर नं. 1, कानपुर नगर न्यायालय</strong> &mdash; व्यक्तियों, परिवारों, भूमिधरों, कर्मचारियों, व्यापारियों एवं छोटे व्यवसायों को परामर्श देता है तथा पहली नोटिस से लेकर विचारण, अपील एवं पुनरीक्षण तक प्रत्येक स्तर पर पैरवी करता है।',
    'about.p2'     : 'चैम्बर की कार्यपद्धति सीधी एवं स्पष्ट है। पहली ही बैठक में मुकदमे का ईमानदार आकलन। समय एवं व्यय का वास्तविक अनुमान। प्रलेखन इतनी सावधानी से तैयार किया जाता है कि वर्षों बाद भी टिका रहे। पक्षकार को वही बताया जाता है जो विधि अनुमति देती है, वह नहीं जो वे सुनना चाहते हैं।',
    'about.t1'     : 'कानपुर नगर के जिला एवं सत्र न्यायालय तथा अधीनस्थ न्यायालयों में पैरवी',
    'about.t2'     : 'अधिकरणों, राजस्व अधिकारियों एवं उपभोक्ता आयोगों के समक्ष उपस्थिति',
    'about.t3'     : 'विलेख, अनुबंध एवं समझौतों का प्रारूपण, परीक्षण एवं रजिस्ट्रीकरण',
    'about.t4'     : 'हिन्दी एवं अंग्रेज़ी में परामर्श',
    'about.caption': 'न्यायालय परिसर में',

    'pr.kicker'    : 'कार्यक्षेत्र',
    'pr.h2'        : 'चैम्बर द्वारा लिए जाने वाले मामले',
    'pr.sub'       : 'यदि आपका मामला यहाँ सूचीबद्ध नहीं है, तब भी अवश्य पूछिए। चैम्बर आपको स्पष्ट रूप से बता देगा कि यह उसके लिए उपयुक्त स्थान है अथवा नहीं।',
    'pr.1h':'सिविल वाद','pr.1p':'घोषणा, कब्ज़ा, निषेधाज्ञा, विनिर्दिष्ट पालन, बँटवारा, वसूली एवं क्षतिपूर्ति के वाद; अपील एवं पुनरीक्षण।',
    'pr.2h':'आपराधिक विधि','pr.2p':'ज़मानत एवं अग्रिम ज़मानत, कार्यवाही निरस्तीकरण, विचारण में बचाव, परिवाद, अपील एवं पुनरीक्षण।',
    'pr.3h':'संपत्ति एवं भूमि','pr.3p':'स्वत्व परीक्षण, विक्रय, दान एवं बँटवारा विलेख, दाखिल-खारिज, सीमा एवं कब्ज़ा विवाद, बिल्डर विवाद।',
    'pr.4h':'राजस्व एवं काश्तकारी','pr.4p':'तहसीलदार, एसडीएम एवं आयुक्त के समक्ष कार्यवाही; भूलेख, वरासत, चकबंदी एवं राजस्व अपील।',
    'pr.5h':'पारिवारिक एवं वैवाहिक','pr.5p':'तलाक, दाम्पत्य अधिकार, भरण-पोषण, अभिरक्षा एवं संरक्षकता, घरेलू हिंसा की कार्यवाही, आपसी समझौते।',
    'pr.6h':'सेवा एवं श्रम','pr.6p':'विभागीय जाँच, सेवा समाप्ति एवं निलंबन, पदोन्नति एवं वरिष्ठता, पेंशन एवं सेवानिवृत्ति देय, श्रम विवाद।',
    'pr.7h':'रिट एवं संवैधानिक','pr.7p':'अनुच्छेद 226 के अंतर्गत राज्य, लोक प्राधिकारियों एवं सांविधिक निकायों के विरुद्ध रिट याचिकाएँ; अवमानना कार्यवाही।',
    'pr.8h':'चेक अनादरण एवं वसूली','pr.8p':'परक्राम्य लिखत अधिनियम की धारा 138 के अंतर्गत परिवाद, विधिक नोटिस, धन वाद एवं निष्पादन।',
    'pr.9h':'मोटर दुर्घटना दावे','pr.9p':'एम.ए.सी.टी. के समक्ष प्रतिकर दावे, बीमा विवाद तथा अपर्याप्त अवार्ड के विरुद्ध अपील।',
    'pr.10h':'उपभोक्ता संरक्षण','pr.10p':'जिला, राज्य एवं राष्ट्रीय आयोग के समक्ष सेवा में कमी तथा अनुचित व्यापार व्यवहार हेतु परिवाद।',
    'pr.11h':'उत्तराधिकार एवं वसीयत','pr.11p':'वसीयत, उत्तराधिकार प्रमाण-पत्र, प्रोबेट एवं प्रशासन-पत्र, पारिवारिक समझौते एवं विरासत विवाद।',
    'pr.12h':'अनुबंध एवं प्रलेखन','pr.12p':'अनुबंध, मुख्तारनामा, पट्टा एवं किरायानामा, नोटिस, शपथ-पत्र एवं वचन-पत्र का प्रारूपण एवं परीक्षण।',

    'ps.kicker'    : 'प्रक्रिया',
    'ps.h2'        : 'पहली कॉल से पहली सुनवाई तक',
    'ps.1h':'अपॉइंटमेंट का अनुरोध','ps.1p':'नीचे दिया फ़ॉर्म भरें अथवा चैम्बर को कॉल करें। अपना शहर तथा विवाद की प्रकृति एक-दो पंक्तियों में बताएँ।',
    'ps.2h':'पुष्टि','ps.2p':'चैम्बर व्हाट्सऐप अथवा फ़ोन पर आपका समय निश्चित कर पुष्टि करेगा और बताएगा कि कौन से कागज़ात लाने हैं।',
    'ps.3h':'परामर्श','ps.3p':'आपके कागज़ात पढ़े जाते हैं, विधिक स्थिति समझाई जाती है, तथा वास्तविक विकल्प, समय एवं व्यय स्पष्ट बताए जाते हैं।',
    'ps.4h':'पैरवी','ps.4p':'आपके निर्णय के पश्चात प्रारूपण आरंभ होता है, मामला दाखिल किया जाता है, तथा प्रत्येक तारीख़ की सूचना आपको दी जाती है।',

    'ap.kicker'    : 'अपॉइंटमेंट',
    'ap.h2'        : 'परामर्श हेतु समय बुक करें',
    'ap.p'         : 'फ़ॉर्म भरिए &mdash; आपका अनुरोध सीधे चैम्बर के व्हाट्सऐप पर पहुँचेगा, अथवा चाहें तो ईमेल से भेजिए। बैठक से पूर्व आपको दिनांक एवं समय की पुष्टि प्राप्त होगी।',
    'ap.t1'        : 'चैम्बर <strong>सोमवार से शनिवार</strong> तक; रविवार एवं न्यायालय अवकाश के दिन बंद',
    'ap.t2'        : 'बाहर के पक्षकारों हेतु टेलीफ़ोन एवं वीडियो परामर्श उपलब्ध',
    'ap.t3'        : 'कृपया समस्त मूल दस्तावेज़ तथा प्राप्त नोटिस अथवा आदेश साथ लाएँ',
    'ap.t4'        : 'आपकी जानकारी केवल परामर्श तय करने एवं करने हेतु प्रयोग की जाती है',
    'ap.call'      : 'चैम्बर को कॉल करें',
    'ap.wa'        : 'व्हाट्सऐप',

    'f.name':'पूरा नाम','f.name.ph':'आपका पूरा नाम',
    'f.phone':'मोबाइल नंबर','f.phone.ph':'10 अंकों का मोबाइल नंबर',
    'f.email':'ईमेल','f.email.opt':'(वैकल्पिक)','f.email.ph':'name@example.com',
    'f.city':'शहर / ज़िला','f.city.ph':'जैसे कानपुर नगर',
    'f.mode':'परामर्श का माध्यम','f.mode.1':'चैम्बर में','f.mode.2':'टेलीफ़ोन','f.mode.3':'वीडियो कॉल',
    'f.matter':'मामले की प्रकृति','f.select':'कृपया चुनें',
    'f.m1':'सिविल वाद / संपत्ति विवाद','f.m2':'आपराधिक मामला / ज़मानत','f.m3':'राजस्व अथवा भूलेख मामला',
    'f.m4':'पारिवारिक अथवा वैवाहिक मामला','f.m5':'सेवा अथवा श्रम मामला','f.m6':'रिट याचिका',
    'f.m7':'चेक अनादरण / धन वसूली','f.m8':'मोटर दुर्घटना दावा','f.m9':'उपभोक्ता परिवाद',
    'f.m10':'उत्तराधिकार, वसीयत अथवा प्रोबेट','f.m11':'प्रारूपण अथवा प्रलेखन','f.m12':'अन्य / निश्चित नहीं',
    'f.date':'इच्छित दिनांक','f.time':'इच्छित समय','f.t6':'कोई भी समय &mdash; चैम्बर तय करे',
    'f.brief':'मामले का संक्षिप्त विवरण','f.brief.ph':'दो-तीन पंक्तियों में: क्या हुआ, कब हुआ, तथा मामला किस स्तर पर है।',
    'f.consent':'मैं समझता/समझती हूँ कि यह फ़ॉर्म भेजने से अधिवक्ता&ndash;पक्षकार संबंध स्थापित नहीं होता, तथा परामर्श होने तक कोई विधिक सलाह नहीं दी जाती।',
    'f.sendwa':'व्हाट्सऐप पर अनुरोध भेजें','f.sendmail':'इसके स्थान पर ईमेल से भेजें',
    'f.note':'<strong>कृपया ध्यान दें:</strong> यदि आप अपनी जानकारी <strong>ईमेल</strong> से भेजते हैं, तो कृपया उसी विषय में <a href="tel:+919450132436">फ़ोन कॉल</a> पर चैम्बर को सूचित भी कर दें, जिससे आपका संदेश छूट न जाए।',

    'pay.kicker':'परामर्श शुल्क','pay.h3':'यूपीआई से भुगतान',
    'pay.p':'किसी भी यूपीआई ऐप &mdash; गूगल&nbsp;पे, फ़ोनपे, पेटीएम, भीम अथवा अपने बैंक के ऐप &mdash; से कोड स्कैन कर परामर्श शुल्क का भुगतान करें।',
    'pay.id':'यूपीआई आईडी',
    'pay.warn':'भुगतान से पूर्व कृपया राशि की पुष्टि चैम्बर से फ़ोन पर कर लें तथा लेन-देन का संदर्भ सुरक्षित रखें। चैम्बर कभी भी ओटीपी, पिन अथवा कार्ड विवरण नहीं माँगता &mdash; यदि कोई माँगे, तो वह हम नहीं हैं।',

    'ct.kicker':'संपर्क','ct.h2':'चैम्बर एवं संपर्क विवरण',
    'ct.ch':'चैम्बर',
    'ct.cp':'<strong>जीनियस सीनियर एडवोकेट एंड एसोसिएट्स</strong><br><strong>चैम्बर नं. 1</strong><br>कानपुर नगर न्यायालय<br>जिला एवं सत्र न्यायालय परिसर, कानपुर नगर',
    'ct.ph':'दूरभाष','ct.wa':'व्हाट्सऐप पर संदेश भेजें',
    'ct.em':'ईमेल','ct.emnote':'ईमेल भेजने के पश्चात कृपया उसी विषय में चैम्बर को फ़ोन कॉल पर सूचित भी कर दें।',
    'ct.hr':'चैम्बर का समय','ct.hrp':'सोमवार &ndash; शनिवार<br>प्रातः एवं सायंकालीन बैठक, पूर्व अपॉइंटमेंट पर<br>रविवार एवं न्यायालय अवकाश: बंद',

    'ft.name':'डॉ. ओम प्रकाश गुप्ता &mdash; वरिष्ठ अधिवक्ता',
    'ft.sub':'जीनियस सीनियर एडवोकेट एंड एसोसिएट्स &bull; चैम्बर नं. 1, कानपुर नगर न्यायालय',
    'ft.legal':'इस वेबसाइट की सामग्री केवल सामान्य जानकारी हेतु है तथा विधिक परामर्श नहीं है। इस वेबसाइट को देखने अथवा अपॉइंटमेंट अनुरोध भेजने से अधिवक्ता&ndash;पक्षकार संबंध स्थापित नहीं होता। भारतीय विधिज्ञ परिषद के नियमों के अनुसार यह वेबसाइट विज्ञापन अथवा कार्य की याचना नहीं है।',
    'ft.copy':'जीनियस सीनियर एडवोकेट एंड एसोसिएट्स।',
    'fab.call':'चैम्बर को कॉल करें','fab.wa':'चैम्बर को व्हाट्सऐप पर संदेश भेजें',

    'err.name'   : 'कृपया अपना पूरा नाम लिखें।',
    'err.phone'  : 'कृपया 10 अंकों का सही भारतीय मोबाइल नंबर लिखें।',
    'err.email'  : 'कृपया सही ईमेल पता लिखें, अथवा इसे खाली छोड़ दें।',
    'err.matter' : 'कृपया मामले की प्रकृति चुनें।',
    'err.time'   : 'कृपया इच्छित समय चुनें।',
    'err.date'   : 'कृपया इच्छित दिनांक चुनें।',
    'err.past'   : 'कृपया कल अथवा उसके बाद की तिथि चुनें।',
    'err.sunday' : 'रविवार को चैम्बर बंद रहता है। कृपया अन्य दिन चुनें।',
    'err.consent': 'आगे बढ़ने हेतु कृपया ऊपर दी गई बात स्वीकार करें।',
    'st.wa'      : 'व्हाट्सऐप आपके अनुरोध के साथ खुल गया है। चैम्बर तक पहुँचाने हेतु वहाँ &ldquo;भेजें&rdquo; दबाएँ।',
    'st.mail'    : 'आपका ईमेल ऐप अनुरोध के साथ खुल गया है। कृपया वहाँ &ldquo;भेजें&rdquo; दबाएँ।',

    'msg.title':'अपॉइंटमेंट अनुरोध','msg.name':'नाम','msg.mobile':'मोबाइल','msg.email':'ईमेल',
    'msg.city':'शहर / ज़िला','msg.mode':'माध्यम','msg.matter':'मामले की प्रकृति',
    'msg.date':'इच्छित दिनांक','msg.time':'इच्छित समय','msg.brief':'संक्षिप्त विवरण',
    'msg.from':'चैम्बर की वेबसाइट से भेजा गया।','msg.locale':'hi-IN'
  }
};

/* ------------------------------------------------------------------ */
var SiteLang = (function () {
  'use strict';
  var KEY = 'siteLang';
  var current = 'en';

  function dict() { return I18N[current] || I18N.en; }

  function t(key) {
    var d = dict();
    return Object.prototype.hasOwnProperty.call(d, key) ? d[key] : (I18N.en[key] || '');
  }

  /* strings hold entities such as &mdash;, so decode before using as plain text */
  var decoder = document.createElement('textarea');
  function plain(key) {
    decoder.innerHTML = t(key);
    return decoder.value;
  }

  function apply(lang) {
    current = (lang === 'hi') ? 'hi' : 'en';

    document.documentElement.lang = current;
    document.title = plain('html.title');

    var each = function (sel, fn) {
      Array.prototype.forEach.call(document.querySelectorAll(sel), fn);
    };
    each('[data-i18n]',      function (el) { el.textContent = plain(el.getAttribute('data-i18n')); });
    each('[data-i18n-html]', function (el) { el.innerHTML  = t(el.getAttribute('data-i18n-html')); });
    each('[data-i18n-ph]',   function (el) { el.placeholder = plain(el.getAttribute('data-i18n-ph')); });
    each('[data-i18n-aria]', function (el) { el.setAttribute('aria-label', plain(el.getAttribute('data-i18n-aria'))); });
    each('[data-i18n-title]',function (el) { el.setAttribute('title', plain(el.getAttribute('data-i18n-title'))); });

    each('[data-lang-btn]', function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-lang-btn') === current ? 'true' : 'false');
    });

    try { localStorage.setItem(KEY, current); } catch (e) { /* private mode */ }

    document.dispatchEvent(new CustomEvent('langchange', { detail: { lang: current } }));
  }

  function initial() {
    var stored = null;
    try { stored = localStorage.getItem(KEY); } catch (e) { stored = null; }
    if (stored === 'hi' || stored === 'en') { return stored; }
    var nav = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
    return nav.indexOf('hi') === 0 ? 'hi' : 'en';
  }

  function init() {
    apply(initial());
    Array.prototype.forEach.call(document.querySelectorAll('[data-lang-btn]'), function (b) {
      b.addEventListener('click', function () { apply(b.getAttribute('data-lang-btn')); });
    });
  }

  return { init: init, apply: apply, t: t, plain: plain, get current() { return current; } };
})();
