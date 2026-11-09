# Parameter dataset research report (text extraction)

> **Provenance:** automated `pdftotext -layout` extraction of `docs/parameter_dataset.pdf`
> (the authoritative copy, supplied by the research team as
> "Falcon 9-Class Reusable LOX_RP-1 Booster: Verified Parameter Dataset for an Engine-Cluster-Size Study").
> Table layout is partly scrambled by the extraction; consult the PDF for any table value.
> Source codes S1-S20 match `data/parameters_baseline.json` `meta.sources`.

```text
Falcon 9–Class Reusable LOX/RP-1 Booster: Verified Parameter Dataset for an
Engine-Cluster-Size Study

Bottom line: SpaceX itself publishes only a small set of numbers: per-engine sea-level thrust (845 kN), minimum throttle
(108,300 lbf out of 190,000 lbf, which is 57%), liftoff mass (549,054 kg), expendable LEO payload (22,800 kg), upper-stage
thrust and burn time (981 kN, 397 s), and launch-site coordinates. spacex Every Falcon 9 mass breakdown (dry mass,
propellant split, landing propellant) and every specific impulse value is an unofficial estimate, including the widely used
Dresia et al. (2021) Table A1. For a cluster-size study, the published 57% throttle floor is likely to be the deciding constraint,
not engine dry mass.

TL;DR

      Official SpaceX values are few. The Falcon User’s Guide (March 2025 edition) and spacex.com give 845 kN per
      Merlin 1D at sea level and a throttle range of 190,000 down to 108,300 lbf (57%). They also give 549,054 kg liftoff
      mass, 22,800 kg to LEO (expendable), and an upper stage of 981 kN for 397 s. All Falcon 9 dry mass, propellant and Isp
      values are unofficial. Dresia et al. (2021) list 27.2 t structural mass, 418.7 t propellant and 25.0 t landing propellant, and
      the authors call these “unofficial estimations.”

      Landing throttle, not engine mass, likely drives the answer. At a fixed 7,605 kN total thrust, one engine at 57% gives
      landing thrust-to-weight (T/W) of about 1.6–1.8, depending on the landing mass assumed. Getting T/W ≤ 1 at
      minimum throttle would need about 15 or more engines. Allowing T/W ≤ 3 (a DLR feasibility threshold) needs about 5
      or more. The classic linearAkin engine-mass formula adds only 59 kg per extra engine, so engine-mass penalties from
      clustering are second-order unless you use a power-law relationship.

      Use published values as anchors, and calibrate the rest. Generic mass formulas overpredict Merlin 1D mass by
      about 1.8× (Akin) to 2.7× (older log-law fit). Scale your formula to the Merlin data point (about 470 kg, secondary
      source) and run sensitivity cases over throttle floor (40–70%), landing propellant (15–35 t) and the engine-mass
      exponent.

Key Findings

  1. Thrust values in official sources don’t fully agree. The 2025 User’s Guide text says 845 kN per engine and 7,605 kN
      total. Table 2-1 in the same document says 7,686 kN, spacex which is 9 × 854 kN, a figure carried over from the 2021
      guide. mit mit 1,710,000 lbf converts to 7,606.5 kN. Use 845 kN and 7,605 kN, and treat 7,686 kN as a leftover from
      the older guide.

  2. Minimum throttle is officially 57% (Block 5, sea level). mit spacex For the 2013 Merlin 1D, SpaceX gave a range of
      70–100 percent, quoted by NASASpaceFlight in March 2013: “Added throttle capability for range from 70-100
      percent”. The 39–40% “deep throttle” claim has no primary source. The 2009 guide states the Merlin 1C (Falcon 9
      v1.0) had no throttling. spaceflightnow

  3. Engine mass and T/W are not officially published. SpaceX says only that Merlin has “the highest thrust-to-weight
      ratio of any boost engine ever made” (User’s Guide). mit spacex The “>150” vacuum T/W claim dates from the 2013
      qualification of the 147,000 lbf version (NASASpaceFlight, citing SpaceX). nasaspaceflight The 470 kg mass appears
      only in secondary sources. Wikipedia +2

  4. Dresia et al. 2021 Table A1 is confirmed as you cited it: 27.2 t structural mass, 418.7 t propellant, 25.0 t landing
      propellant, 569.3 t GLOW, ascent Δv of 3.5 km/s and an assumed landing Δv of 2.0 km/s. The authors state the values
      “are based on unofficial estimations.” dlr Their GLOW (569.3 t) is 20 t above SpaceX’s 549.054 t, so their mass split
      doesn’t add up to the official total. dlr spacex

  5. Published cluster-size results point in different directions and depend on the mass model. Dresia’s optimizer
      chose 5–6 first-stage engines, but the authors warn this is because their mass relationships “only consider the engine
      mass as a function of the engine thrust.” dlr DLR’s VTVL designs with fixed generic engines ended up with 15–17
      hydrocarbon engines. dlr DLR notes that small stages can’t land safely if T/W exceeds 3 even at 30% throttle, and
      that a European reusable engine would need 33–100% throttling to land with T/W near 1. dlr dlr
Source Key (cited by code in tables)

Code Source                                                                                       Type

S1 SpaceX, Falcon User’s Guide, version 8 (change log: March 2025), file dated 2025-05-09.        Official
         https://www.spacex.com/assets/media/falcon-users-guide-2025-05-09.pdf

S2 SpaceX, Falcon User’s Guide, September 2021 (version 7), copy hosted by MIT.                   Official (third-party
         https://web.mit.edu/2.70/Reading%20Materials/SpaceX%20Falcon-users-guide-2021-09.pdf     mirror)

S3 SpaceX, “Falcon 9” vehicle page, accessed Nov 2026. https://new.spacex.com/vehicles/falcon-9 Official

S4 SpaceX, Falcon 9 Launch Vehicle Payload User’s Guide, 2009 (v1.0 era).                         Official (historical)
         https://www.spaceflightnow.com/falcon9/001/f9guide.pdf

S5 Dresia, K., Jentzsch, S., Waxenegger-Wilfing, G., Dos Santos Hahn, R., Deeken, J., Oschwald, M., Peer-reviewed (its

Mota, F., “Multidisciplinary Design Optimization of Reusable Launch Vehicles for Different        Falcon 9 data are

Propellants and Objectives,” J. Spacecraft and Rockets, 58(4), 2021, pp. 1017–1029,               unofficial estimates)

doi:10.2514/1.A34944. altmetric Open access: https://elib.dlr.de/141082/1/1.A34944.pdf

S6 Stappert, S., Wilken, J., Sippel, M., Dumont, E., “Assessment of a European Reusable VTVL      Conference (DLR)
         Booster Stage,” Space Propulsion 2018, SP2018_00478, Seville.
         https://elib.dlr.de/121410/2/478_STAPPERT.pdf

S7 Akin, D. L., “Mass Estimating Relations,” ENAE 791 lecture notes, Univ. of Maryland, 2016.     Academic/secondary
         https://spacecraft.ssl.umd.edu/academics/791S16/791S16L08.MERsx.pdf

S8 Zandbergen, B. T. C., “Simple mass and size estimation relationships of pump fed rocket engines Conference
         for launch vehicle conceptual design,” 6th EUCASS, 2015 (via ResearchGate)

S9 Zilker, F., “Aerothermal Analysis of Re-usable First Stage during Rocket Retro-propulsion,” M.Sc. Academic thesis
         thesis, Univ. Stuttgart / DLR, 2018. https://elib.dlr.de/119265/1/SADA_ITLR.pdf

S10 Blackmore, L., “Autonomous Precision Landing of Space Rockets,” The Bridge, 46(4), NAE, 2016, Peer-reviewed

pp. 15–20. http://www.larsblackmore.com/nae_bridge_2016.pdf                                       magazine (SpaceX

                                                                                                  author)

S11 Kyle, E. (Space Launch Report), “SpaceX Falcon 9 v1.2 Data Sheet,” hosted by NASA Safety &    Secondary (on a
         Mission Assurance. https://sma.nasa.gov/LaunchVehicle/assets/spacex-falcon-9-v1.2-data-  government site)
         sheet.pdf

S12 NASASpaceFlight, “Falcon 9 boost as Merlin 1D engine achieves major milestone,” March 2013. Secondary
         https://www.nasaspaceflight.com/2013/03/falcon-9-boost-merlin-1d-engine-achieves-
         milestone/

S13 Wikipedia, “SpaceX Merlin,” “Falcon 9,” “Falcon 9 Full Thrust” (accessed Nov 2026)            Unofficial

S14 shahar603, “Telemetry-Data” (webcast-extracted), SpaceX CRS-16 dataset, GitHub                Unofficial

S15 NASASpaceFlight forum thread quoting the SpaceX CRS-3 press kit (2014).                       Secondary (quotes
         https://forum.nasaspaceflight.com/index.php?topic=34464.0                                official press kit)
Code Source                                                                                    Type

S16 SpaceX on X, 26 Jan 2023 (Starlink 5-2): “56 Starlink satellites—weighing in total more than 17.4 Official (secondary
         metric tons—marking the heaviest payload ever flown on Falcon”. Also reported by Space.com / reports agree)
         Yahoo News, “SpaceX launches heaviest payload on reused rocket’s 9th flight,” Jan 2023, and by
         Spaceflight Now

S17 DLR SART: Sippel et al., IAF 2022 paper (https://elib.dlr.de/195201/1/IAF22-2.pdf); SLME system Conference (DLR)
         studies, Space Propulsion 2022 (https://elib.dlr.de/186560/1/SP-
         2022_Systematic_Studies_on_Reusable_Staged-
         Combustion_Rocket_Engine_SLME_for_European_Applications.pdf)

S18 Engine data compiled by a research sub-agent from: ULA Delta II heritage page; Pratt &     Mixed (marked per

Whitney/NPO Energomash RD-180 fact sheet (via Spaceflight Now, 2002); Roscosmos 2012           row)

reproduction of Energomash tables; SpaceX post on X, 3 Aug 2024 (Raptor 1/2/3); Rocket Lab

Electron page; Metal AM, May 2026; NASASpaceFlight, Nov 2016 (YF-100); Blue Origin fact

sheet via Spaceflight Now, 2014; enginehistory.org; Purdue AAE; Astronautix. Search snippets

only, full pages not opened.

S19 Wevolver spec pages (aggregator of uncertain origin)                                       Unofficial

S20 Marwege, A. et al., “RETALT: review of technologies and overview of design changes,” CEAS  Peer-reviewed
         Space Journal, 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9244295/

Confidence scale: High = official or primary, checked in the full document. Medium = peer-reviewed or reputable
secondary source, or official but internally inconsistent. Low = unofficial, single source, or snippet only.
A. Engine: Merlin 1D (sea level) and earlier versions

Parameter Value                 Units Version Source Page/Table Source type Confidence Notes

Sea-level 845 (190,000 kN Block 5 / S1; S3 S1 §2.3                   Official      High    Current official
                                                                                           value. spacex
thrust, per lbf) spacex             current

engine

Sea-level 854 (190,000 kN FT/Block S2                   §2.3         Official      Medium  190,000 lbf is
                                                                                           actually 845 kN, so
thrust, per lbf) mit                5 (2021)                                               854 is likely a typo.

engine                                                                                      mit

Sea-level    7,605 (text) /     kN  Block 5 S1          §2.3; Table  Official      Medium  Internal mismatch.
thrust, 9-                                              2-1                                7,686 = 9 × 854. Use
engine       7,686 (Table 2-1)                                                             7,605. spacex
total

Sea-level 7,607 Wikipedia kN FT                S5; S13  S5 Table     Peer-         Medium  Matches 1,710,000
thrust, 9-                                              A1           reviewed /            lbf. Wikipedia
engine                                                               unofficial
total

Vacuum 8,227 (914 per kN FT                    S5; S13  S5 Table     Peer-         Medium  No current official
                                                        A1           reviewed              vacuum value for
thrust, 9- engine) dlr                                               (unofficial           the sea-level Merlin.
                                                                     data)
engine       Wikipedia                                                                      Wikipedia

total

Sea-level 556 (125,000 kN Merlin S4                     —            Official      High    v1.0 had 9 engines in
                                                                                           a 3×3 grid.
thrust, per lbf) Wikipedia          1C (v1.0)                        (historical)
                                                                                            Wikipedia
engine                                                                                      spaceflightnow
                                                                                            Wikipedia

Stage sea- 5,885 / 6,672        kN v1.1        S13      —            Unofficial Low        v1.1 used early
                                                                                           Merlin 1D, about
level /      Wikipedia                                                                     147,000 lbf per
                                                                                           engine.
vacuum
                                                                                            nasaspaceflight
thrust                                                                                      Wikipedia

Sea-level /  282 / 311          s   v1.1 era, S13       —            Unofficial Low        Wikipedia marks
vacuum                                                                                     these “needs
Isp           Wikipedia             still                                                  update.” Wikipedia

                                    widely

                                    quoted

Sea-level / 283 / 312 dlr       s   FT/Block S5         Table A1     Peer-         Medium  SpaceX publishes no
                                    5                                reviewed              Isp for the sea-level
vacuum                                                               (unofficial           Merlin.
                                                                     data)
Isp
Parameter Value           Units Version Source Page/Table Source type Confidence Notes

Dry mass ~470 Wikipedia kg    Merlin S13          —     Unofficial Low     No primary source
                                                                           found. Wikipedia
                              1D                                           and Wikidata
                                                                           (Q19923939) both
                              (version                                     list 470 kg with no
                                                                           SpaceX citation.
                              unclear)                                     Astronautix gives
                                                                           490 kg for an early
                                                                           version.

Thrust-to- >150 (vacuum) –    Merlin    S12       —     Secondary Medium   NASASpaceFlight,
                              1D, 147                                      March 2013: “The
weight  nasaspaceflight       klbf      (citing                            Merlin 1D has a
                              version                                      vacuum thrust-to-
                              (2013)    SpaceX)                            weight ratio
                                                                           exceeding 150, the
                                                                           best of any liquid
                                                                           rocket engine in
                                                                           history.” The 28-test
                                                                           qualification
                                                                           program ran 1,970 s,
                                                                           including four tests
                                                                           at or above 147,000
                                                                           lbf for 185 s.

Thrust-to- “highest of any –  Block 5 S1          §2.3  Official   High    Qualitative only.

weight  boost engine                                                        spacex

        ever made” (no

        number) mit

Thrust-to- ~184 (845 kN ÷ –   Block 5   S13;      —     Unofficial / Low   Only as good as the
                                                        derived            470 kg mass.
weight  (470 kg × 9.81))                derived
                                                                            Wikipedia
        Wikipedia

Minimum 108,300 of        %   Block 5 S1; S2 Table 2-1 Official    High    Best value for this
                                                                           study. mit spacex
throttle 190,000 lbf =        (sea

        57% mit               level)

Minimum 70% (range 70– %      Early     S12       —     Secondary  Medium  SpaceX statement
throttle 100 percent)         Merlin                    (quotes            quoted by
                              1D        (quoting        SpaceX)            NASASpaceFlight
                              (2013)                                       (Chris Bergin,
                                        SpaceX)                            March 2013): “Added
                                                                           throttle capability
                                                                           for range from 70-
                                                                           100 percent.”
Parameter Value              Units Version Source Page/Table Source type Confidence Notes

Minimum    ~39–40%           %  Claimed Forums —      Unofficial Low        Unverified. Use only
throttle                                                                    as a sensitivity case.
                                for      only
                                                                             nasaspaceflight
                                Merlin                                       spacelaunchlive

                                1D

Throttle None                –  Merlin S4 (via —      Official      Medium  spaceflightnow
                                                      (historical)
                                1C (v1.0) S18)

Chamber 9.7 (1,410 psi) MPa Merlin S13          —     Unofficial Low        Other unofficial
                                                                            values: 10.8 MPa
pressure                        1D                                          (S19, “1D++”); 9.6
                                                                            MPa (Astronautix,
                                                                            MVac). astronautix

                                                                             Wikipedia +2

Mixture 2.36                 –  “Merlin- S19    —     Unofficial Low        Consistent with RP-
ratio (O/F)                                                                 1 gas-generator
                                1D++”                                       practice. wevolver

Nozzle     16                –  Merlin S19      —     Unofficial Low        DLR used ε = 20 for
                                                                            generic reusable
expansion                       1D                                          gas-generator
                                                                            engines (S6). dlr
ratio
                                                                             wevolver

Throat / 0.042 / 0.90        m² Merlin S19      —     Unofficial Low        0.90 m² means about
                                                                            1.07 m exit diameter,
exit area                       1D                                          which conflicts with
                                                                            the 0.92 m engine
                                                                            diameter on
                                                                            Wikipedia.

                                                                             Wikipedia
                                                                             wevolver

Propellant ~305 (845 kN ÷ kg/s  Block 5  Derived —    Engineering Low       Not published.
mass flow (282 s × g₀))                               estimate              Calculated from
                                                                            thrust and Isp.

Engine Gas generator; –         Merlin S1       §2.3  Official      High    Steering hydraulics
                                                                            use RP-1 as the
cycle      single-shaft         1D                                          working fluid. mit

           turbopump;                                                        spacex

           pintle injector;

           regeneratively

           cooled copper-

           alloy liner mit

Restart    Yes mit           –  Merlin S1       Table 2-1 Official  High    spacex

                                1D
Parameter Value             Units Version    Source   Page/Table Source type Confidence Notes
                                             S9; S11
Boostback 3 dlr nasa        count   FT                S9 §1.2  Thesis /   Medium  Drone-ship missions
engines                             (when    S9; S11           secondary          often skip boostback
                                    flown)   S11; S9                              or do a partial one.

Entry burn 3 (about 20 s)   count, FT/v1.2            —        Thesis /   Medium
                            s
engines  nasa                                                  secondary

Landing  1 (center engine,  count,  FT/v1.2           —        Secondary Medium 32 s is from one
burn     about 32 s)        s
engines  usually; a 3-                                                            flight entry in S11.
         engine landing
         burn has been                                                            Wikipedia
         tried nasa
B. First stage / booster

Parameter         Value            Units Version Source Page/Table Source type Confidence Notes

Liftoff mass      549,054 spacex kg    Current S3       Overview Official     High
(full vehicle)                         (FT/Block
                                       5)

Liftoff mass      569.3 dlr        t   “v1.2     S5     Table A1 Peer-        Medium 20 t more than

                                       Block 5”                  reviewed             official.

                                                                 (unofficial

                                                                 data)

Liftoff mass 505,846 / 333,400 kg      v1.1 / v1.0 S13  —        Unofficial Low

                  tesla

First-stage       27.2 dlr         t   Block 5 S5       Table A1 Peer-        Medium Confirmed as
structural (dry)
mass                                                             reviewed             you cited it.

                                                                 (unofficial

                                                                 data)

First-stage       25,600 wevolver kg   Block 5 S19      —        Unofficial Low       Origin
                                                                                      unknown.
“empty mass”                                                                          Community
                                                                                      estimates run
                                                                                      about 22–27 t.

First-stage       418.7 dlr        t   Block 5 S5       Table A1 Peer-        Medium
propellant
                                                                 reviewed

                                                                 (unofficial

                                                                 data)

Landing           25.0 dlr         t   Block 5 S5       Table A1 Peer-        Medium From reverse
propellant
(drone ship)                                                     reviewed             engineering.

                                                                 (unofficial          Optimizer

                                                                 data)                gave 26.6 t.

                                                                                      dlr

Landing Δv        2,000 (includes m/s  Block 5 S5       §II.B.2  Peer-        Medium  A modeling
                  5% margin), for                                reviewed             assumption.
                  3,500 ascent Δv

                   dlr

Descent           7–9% of stage    %   DLR       S6     §4       Conference Medium    For drone-
                                                                                      ship landing.
propellant        GLOM                 concepts

share             (hydrocarbon

                  DLR stages) dlr

Diameter          3.66 (SpaceX also m  All       S1; S3 Table 2-1 Official    High    spacex

                  rounds to 3.7)

                  mit
Parameter    Value                Units Version Source Page/Table Source type Confidence Notes

First-stage  41.2 (47.7 with      m   FT/Block  S19; S13  Table A1  Unofficial /  Low–    Not on the
length                                5         / S5                peer-         Medium  current official
             interstage) / 40.9                                     reviewed              page.

             dlr wevolver

Recovery     4 grid fins, 4       count FT/Block S1; S3 §2.3        Official      High    No masses
hardware                                                                                  published.
             deployable legs          5
                                                                                           spacex
             mit

Legs + grid fins Not publicly     %   Model S5            §II.A     Peer-         Low     DLR (S6)
                                                                                          scales leg and
mass         available. Proxy:                                      reviewed              fin mass
                                                                                          linearly with
             +15% of first-                                                               dry mass and
                                                                                          calls this
             stage dry mass                                                               conservative.

             dlr                                                                           dlr

Engine share of ~16% (9 × 470 kg %    Block 5   Derived —           Engineering Low       Dresia’s
                                                from                estimate              optimized RP-
dry mass     ÷ 27.2 t)                          S13, S5                                   1 first stages
                                                                                          have
                                                                                          propulsion
                                                                                          (engines +
                                                                                          steering) at
                                                                                          about 28% of
                                                                                          structural
                                                                                          mass. dlr

Expendable   22,800 spacex        kg  Current S3          Overview Official       High    Target orbit
                                                                                          not stated by
LEO payload                                                                               SpaceX.

                                                                                           Wikipedia

Reusable LEO >17,400 (56          kg  Block 5   S16       —         Official      High    SpaceX: “56
                                                                                          Starlink
payload      Starlink, Starlink                 (SpaceX                                   satellites—
                                                                                          weighing in
(demonstrated) 5-2, 26 Jan 2023;                on X)                                     total more
                                                                                          than 17.4
             booster B1067 on                                                             metric tons—
                                                                                          marking the
             its 9th flight,                                                              heaviest
                                                                                          payload ever
             landed on drone                                                              flown on
                                                                                          Falcon.”
             ship JRTI)                                                                   Spaceflight
                                                                                          Now (Stephen
Parameter     Value              Units  Version  Source  Page/Table  Source type  Confidence  Notes

                                                                                              Clark)
                                                                                              reported
                                                                                              “more than
                                                                                              38,000
                                                                                              pounds.”
                                                                                              About 24%
                                                                                              below
                                                                                              expendable.

Reusable LEO  17,500 / 18,500    kg     FT/Block S13     —           Unofficial Low           Wikipedia
payload                                                                                       pages
(quoted        Wikipedia                5                                                     disagree with
capability)    Wikipedia                                                                      each other.

                                                                                               Wikipedia

                                                                                               Wikipedia

GTO payload,  8,300 / ~5,500     kg     FT/Block S3 / S6; —          Official /   High /      About a 34%
expendable /                                                         conference   Medium      penalty for
drone ship     Wikipedia                5        S13                                          reuse.
               spacex
                                                                                               Wikipedia

MECO (v1.1,   t ≈ 161 s, h ≈ 80  s, km v1.1      S15     —           Secondary    Medium
CRS-3)        km, about Mach                                         (quotes
              10                                                     press kit)
MECO (Block
5, CRS-16,     nasaspaceflight   s, m/s, Block 5 S14     —           Unofficial Low           A return-to-
RTLS)                                                                                         launch-site
              145 s; 1,624 m/s;  km                                                           mission, so
              66.9 km; peak                                                                   MECO is
              3.43 g github                                                                   earlier and
                                                                                              slower than
MECO for LEO  Not publicly       –      –        –       –           –            –           drone-ship
drone-ship    available                                                                       missions.
missions;
flight-path                                                                                   Proxy: extract
angle                                                                                         from webcast
                                                                                              telemetry for a
Landing       ~300 (CRS-8)       km FT           S13     —           Unofficial Low           specific
distance                                                                                      drone-ship
downrange      Wikipedia                                                                      mission (S14
                                                                                              method).

                                                                                              Varies by
                                                                                              mission.
Parameter        Value                Units   Version  Source  Page/Table Source type Confidence Notes
Entry burn                                    FT       S9; S6
start altitude   ~70–50 (F9 about km                           S6 §4  Thesis /     Medium  DLR’s
                 50) dlr dlr                           –              conference           reconstruction
Touchdown                                                                                  of the SES-10
velocity                                               S6                                  flight.

Reentry q /      Not publicly         m/s –                    –      –            –       Proxy: about 2
heating limits   available
(model)                                                                                    m/s or less

Retro-                                                                                     (engineering
propulsion
heating                                                                                    assumption).

Drag             q < 200 kPa;         kPa, g  DLR              §3.4   Conference Medium These are
coefficient for  lateral load < 3 g;          model
descent          heat flux capped                                                          model limits,
                 at the SES-10
Precision        reentry value dlr                                                         not SpaceX
landing
approach                                                                                   data.

                 Side wall up to      kW/m²,  DLR 9-   S9      Abstract Thesis     Medium Entry burn
                 ~20 kW/m²; base      K       engine
                 up to ~70 kW/m²;             concept                                      from Mach
                 side wall up to
                 ~400 K (NASA                                                              9.45 to 5.09
                 infrared imaging
                 showed about 450                                                          between 70
                 K) dlr
                                                                                           and 36 km.

                                                                                           dlr

                 Not given            –       Model    S5      Table 1, Eq. Peer-  Low     RETALT1’s
                                                                                           aerodynamic
                 numerically in the                            4      reviewed             database
                                                                                           (S20) is open
                 sources reviewed.                                                         access and is
                                                                                           the best
                 Dresia assumes a                                                          source for
                                                                                           Mach-
                 constant Cd and                                                           dependent Cd.

                 uses √(m/A) ≈                                                              nih

                 1.47–1.62 t^½/m

                 for RP-1 stages

                 dlr

                 Boostback            –       F9R      S10     pp. 15–20 Peer-     Medium Qualitative

                 targeting, grid-fin                                  reviewed             only, no

                 control in the                                       (SpaceX              numbers.

                 atmosphere,                                          author)

                 landing burn;

                 99% of

                 dispersions must

                 fall inside the

                 landing zone

                 nationalacademies

                 larsblackmore
C. Upper stage (Merlin Vacuum)

Parameter Value           Units Version  Source Page/Table Source          Confidence Notes
                                                                     type

Vacuum    981 (220,500 kN Block 5 S1; S3 Table 2-1 Official                High    spacex

thrust    lbf) spacex

          mit

Vacuum    934 / 801 / 617 kN FT / v1.1 / S13 —          Unofficial Low             astronautix Wikipedia
thrust
          Wikipedia          v1.0

Minimum   140,679 of %       Block 5 S1     Table 2-1 Official High                spacex
throttle  220,500 lbf ≈
          64% mit

Vacuum Isp 348 tesla      s  FT/Block S5; S13 Table A1  Peer-              Medium  Not official. Wevolver
                             5                          reviewed                   also lists 348 s. wevolver
          Wikipedia                                     (unofficial
                                                        data)                        Wikipedia

Expansion 165:1, fixed –     Block 5 S1     §2.3        Official High              spacex

ratio     nozzle mit

Burn time 397 spacex s       Block 5 S3     Second      Official High
                                            stage

Dry mass 4.5 dlr          t  Block 5 S5     Table A1 Peer-                 Medium

                                                        reviewed

                                                        (unofficial

                                                        data)

Propellant 111.5 dlr      t  Block 5 S5     Table A1 Peer-                 Medium Older secondary figure:

                                                        reviewed                   92,670 kg (Leitenberger,

                                                        (unofficial                v1.1 era).

                                                        data)                      bernd-leitenberger

Fairing   5.2 diameter m Current S1         §4.1        Official High              Composite: aluminum
                                                                                   honeycomb with carbon-
dimensions × 13.2 height                                                           fiber skins (S2). mit

          (extended                                                                 spacex

          version 18.7)

          mit

Fairing   Not publicly kg –              –  –           –                  –       Proxy: Dresia’s “payload
mass;     available                                                                bay” of 7.4 t for a 5.0 t
payload                                                                            payload implies about 2.4
adapter                                                                            t for fairing, adapter and
mass                                                                               avionics bay (S5), or use
                                                                                   Akin’s fairing formula m
                                                                                   = 4.95·A^1.15 (S7). dlr

                                                                                    umd
Parameter  Value  Units Version  Source Page/Table Source          Confidence Notes
                                                             type
Adapter
capacity   1,575 mm: up kg  Current S1  Table 4-1 Official         High  Structural limits, not
           to 10,885 kg;                                                 performance. spacex
           2,624 mm: up
           to 19,050 kg;
           3,117 mm
           strut: up to
           26,500 kg
D. Mission / constraints       Units Version  Source  Page/Table Source     Confidence Notes
                                                                      type
Parameter Value

Maximum Not published          kPa –          S1      Acronyms Official –          Proxy: about 30–
                                                                                   35 kPa
dynamic (acronym only)                                                             (community
                                                                                   estimates,
pressure                                                                           unofficial).

(max-Q)                                                                             nasaspaceflight +3

Payload    Axial up to +6.0 g, g   2021       S2      Figs. 4-1, 4- Official High  Limit loads
                                                      2                            including
design load −2 g (payloads >                                                       dynamics, not the
                                                                                   steady-state
factors    1,810 kg); up to                                                        acceleration cap.

           +8.5 g (lighter

           payloads) mit

Steady-    “Both the first- and –  2021       S2      §4.3.1  Official High        The 2009 guide
                                                                                   shows shutting
state      second-stage                                                            down 2 engines
                                                                                   for the
acceleration engines may be                                                        acceleration limit
                                                                                   (v1.0).
control    throttled to help
                                                                                    spaceflightnow
           maintain... steady

           state acceleration

           limits” (no

           number) mit

SLC-40     28.5620° N,         deg –          S2      §6.1.1  Official High

latitude   80.5772° W mit

LC-39A     28.6082° N,         deg –          S2      §6.1.2  Official High

latitude   80.6041° W mit

LEO        28.5–55 (55–65      deg 2025       S1      Table 3-1 Official High      Below 28.5° costs
                                                                                   performance.
inclinations, with a dog-leg
                                                                                    mit spacex
Eastern    penalty)

Range

Mass-to- “available upon –         2021/2025 S1; S2   §3.2    Official High        No official

orbit curves request” mit                                                          performance

                                                                                   curves are

                                                                                   published.

                                                                                   spacex

Orbit for  Not stated by       km, FT         Leitenberger —  Secondary Low        Fits your
22,800 kg  SpaceX.             deg            (secondary)                          provisional 200
figure     Secondary                                                               km target.
           sources: 200 km
           LEO from Cape
Parameter Value               Units Version Source  Page/Table Source     Confidence Notes
                                                                    type

         (~28.5°)

          bernd-leitenberger

Dresia LEO 200 × 200 km;      m/s Model S5          Table 2  Peer-        Medium  Losses assumed:
                                                             reviewed             gravity 1,000–
mission  Δv_orbit 8,030                                                           1,500, drag 100–
                                                                                  150 m/s. dlr
         m/s; Δv with losses

         9,500 m/s dlr
E. Engine mass scaling data and mass estimating relationships (MERs)

E1. Engine table (T/W = thrust ÷ (mass × 9.81) unless the source gives it)

Engine     Sea-level /  Dry mass       T/W Cycle /         Source              Source type Confidence Notes
           vacuum       (kg)                   propellant
           thrust
           (kN)

Merlin 1D  845 / ~914 ~470             ~184 Gas            S1 (thrust); S13 (mass) Official /       Medium /  Mass is undated.
(Block 5)                              (SL) generator /                                 unofficial  Low
                                                                                                               Wikipedia
                                               LOX-RP-1                                                        spacex

Merlin 1C 556 / — Not found — Gas                          S4                  Official             Medium    spaceflightnow
                                                                               (thrust)
(F9 v1.0) Wikipedia                    generator /

                                       LOX-RP-1

F-1        6,770 /      8,353–8,400 ~94 Gas                NASA MSFC (thrust); Government Medium Uprated to

           7,770                       generator / Wikipedia/Astronautix / secondary                          1,522,000 lbf from

                                       LOX-RP-1 (mass)                                                        Apollo 8 onward.

                                                                                                              Wikipedia +2

H-1        912 / —      635 / 911 / ~93– Gas               enginehistory.org   Secondary Low                  The lowest mass
(Saturn                                                    (citing Rocketdyne                                 may leave out
IB)                     ~1,000         146 generator /     manual); Purdue                                    some hardware.

                        (conflicting)  LOX-RP-1                                                                Wikipedia +2

RS-27A 890 / 1,054 1,147               ~79 Gas             ULA Delta II page   Official             High      Wikipedia
                                                                                                              ulalaunch
                                       (SL) generator /

                                       LOX-RP-1

RD-180 3,827 /          5,393–5,480 ~72 Oxygen- P&W/Energomash fact Official                        High      Throttle 40–100%.

           4,152                       rich staged sheet; Roscosmos                                            Wikipedia
                                                                                                               spaceflightnow
                                       combustion

                                       / LOX-RP-1

RD-170 /   7,250 /      9,750          ~76– Oxygen- Energomash via             Near-official Medium           Wikipedia
RD-171M    7,900                       82 rich staged Roscosmos                                               roscosmos

                                               combustion
                                               / LOX-RP-1,
                                               4 chambers

RD-107A    839.5 /      1,190 (RD-     ~72 Gas             Wikipedia           Unofficial Low                 No RD-108A data
           1,019.9      107)                                                                                  found. Wikipedia
                                       generator /

                                       LOX-

                                       kerosene, 4

                                       chambers

NK-33      1,510 /      1,240          ~124 Oxygen- Wikipedia                  Unofficial Low                 Wikipedia
           1,680                               rich staged
                                               combustion
Engine      Sea-level /  Dry mass      T/W Cycle /           Source      Source type Confidence Notes
            vacuum       (kg)                  propellant
            thrust
            (kN)

                                       / LOX-
                                       kerosene

RD-191      1,922 /      2,200         ~89 Oxygen- Energomash via        Near-official Medium         RD-191M throttle
            2,085        (official) /          rich staged Roscosmos                                  27–110%
                         2,290                 combustion                                             (secondary).
                                               / LOX-
                                               kerosene                                                Wikipedia +2

YF-100      1,199 /      Not found     — Oxygen- NASASpaceFlight         Secondary Low                 nasaspaceflight
            1,339                              rich staged 2016
                                               combustion                                              Wikipedia
                                               / LOX-                                                  metal-am
                                               kerosene
                                                                                                       newspaceeconomy
Rutherford  ~24.9 /      35            ~73 Electric          Rocket Lab; Metal AM Official /  Medium    Wikipedia
(small-     25.8         1,630                 pump /
engine                                         LOX-RP-1      2026        trade press                  1,720 kg including
end)                                                                                                  vehicle-side
                                                  Wikipedia                                           hardware. x

Methane:    2,256 / —                  ~141 Full-flow SpaceX on X, 2024  Official             High    ULA fact sheet
                                                                                                      confirms
Raptor 2                               staged                                                         “550,000-lbf
                                                                                                      thrust at sea level.”
                                       combustion                                                     In Nov 2025,
                                                                                                      NASASpaceFlight
                                       / LOX-CH4                                                      reported test-
                                                                                                      stand engines at
Methane:    2,746 / —    1,525         ~184 Full-flow SpaceX on X, 2024  Official             High    “625,000 pounds-
                         (engine                                                                      force under
Raptor 3                 only)         staged                                                         current conditions,
                                                                                                      with plans to reach
                                       combustion                                                     640,000 pounds-
                                                                                                      force… through
                                       / LOX-CH4                                                      propellant

Methane:    2,450        Not found     — Oxygen- Blue Origin via         Official             Medium
            (550,000
BE-4        lbf                        rich staged Spaceflight Now 2014; (thrust) /
            baseline) /
            —                          combustion ULA BE-4 fact sheet; secondary

                                       / LOX-LNG NASASpaceFlight,        (uprate)

                                                             Nov 2025
Engine  Sea-level /  Dry mass  T/W Cycle /         Source  Source type Confidence Notes
        vacuum       (kg)              propellant
        thrust                                                                                subcooling.” That
        (kN)                                                                                  takes the 7-engine
                                                                                              New Glenn
                                                                                              booster from
                                                                                              17,219 kN to 19,928
                                                                                              kN.

The Merlin 1D is an outlier. Its T/W of about 184 is 2–2.5× that of other gas-generator kerosene engines (RS-27A about 79, F-
1 about 94). Any MER fitted to historical engines will overpredict Merlin mass badly unless you calibrate it.
E2. Published MERs

MER                 Functional form            Validity range Source          Source type  Confidence  Check against
                                                                                                       Merlin 1D (845
                                                                                                       kN, ε = 16)

Akin (UMd),         m (kg) = 7.81×10⁻⁴·T(N) +  Not stated       S7, slide 25 Academic      Medium      ≈ 833 kg, which is
liquid pump-        3.37×10⁻⁵·T(N)·√(Ae/At) +  (based on                                               1.8× the 470 kg
fed engine          59                         NASA CR-                                                figure
                                               2420, TM-
                                               78661, TN-D-
                                               6349, JSC-
                                               26098) umd

Akin, thrust        m (kg) = 2.55×10⁻⁴·T(N)    Not stated       S7, slide 25 Academic Medium           7,605 kN total →
structure                                                                                              1.94 t, the same
                     umd                                                                               for any engine
                                                                                                       count

Akin, gimbals       m (kg) =                   Not stated       S7, slide 26 Academic Medium           Depends on
                    237.8·(T/p₀)^0.9375 umd                                                            chamber pressure
                                                                                                       p₀

Zandbergen M-       m = 1.866×10⁻¹⁰·T² +       15 kN–8 MN;      S8, Table 4 Conference Medium          Hydrogen-
C2 (hydrogen-       0.00130·T + 77.4 (T in N)                                                          oxygen only. Do
oxygen)                                         researchgate                                           not use for RP-1.

                                               typical error                                            researchgate
                                               about 13%                                                researchgate

Zandbergen,         Multi-parameter form       15 kN–8 MN;      S8, Table 4   Conference Low           Full coefficients
kerosene and        (thrust, number of         stated accuracy                                         not verified. Get
storable            chambers, expansion        ±10–25%                                                 the paper.
                    ratio). The snippet shows
                    “M = (1.079E-3·THRUST +     researchgate
                    53.0165)·NT^0.0369·…”

Older log law       T/W = 25.2·log₁₀(F[N]) −   Small dataset S8               Conference Low           T/W ≈ 69, so mass
(cited as ref. [5]  80.7                       (8 engines)                    (secondary)              ≈ 1,250 kg (2.7×)
in Zandbergen)
                                                                                                        researchgate
Castellini          Engine mass as a function  —                S5 (citing Peer-           Low
(2012), used by     of thrust only dlr                                                                 Exact form not
Dresia                                                          Castellini, reviewed                   retrieved

                                                                PhD thesis, (indirect)                 Exponents not
                                                                                                       verified
                                                                Politecnico
                                                                                                        semanticscholar
                                                                di Milano)

Rohrschneider       Not retrieved              —                Georgia       Academic —
(2002), Georgia
Tech MER                                                        Tech SSDL
database
                                                                M.S. project
MER          Functional form  Validity range Source  Source type  Confidence  Check against
                                                                              Merlin 1D (845
                                                                              kN, ε = 16)

Tizón &      Not retrieved    —  —                   —            —           Not verified
Román, AIAA
2017-5010

What the MERs mean for engine count at fixed total thrust: With Akin’s linear form, total engine mass is 7.02 t + 0.059 t ×
N for 7,605 kN at ε = 16. That gives about 7.08 t for N = 1, 7.55 t for N = 9 and 8.61 t for N = 27. Clustering costs only about 59
kg per engine, so engine dry mass alone won’t decide the optimum. A power-law MER with exponent below 1 would make
the clustering penalty larger. The hydrogen-oxygen quadratic does the opposite: it penalizes big engines. So the result
depends on which formula you choose, and you should report it across a range of exponents.

E3. Thrust-structure and multi-engine relationships

      Akin: thrust structure scales only with total thrust (2.55×10⁻⁴ kg/N) and does not depend on engine count (S7). umd
      DLR uses empirical formulas for thrust frame, engine equipment, steering, controllers and harness inside its stsm
      tool. dlr Their exact form isn’t published in S6 (S6 §3.3).
      No published relationship that ties thrust-structure mass explicitly to engine count was found. Not publicly
      available. A defensible proxy: Akin’s formula plus a per-engine add-on for steering, plumbing and controller
      hardware, varied in sensitivity runs (engineering assumption).
F. Published studies on engine count for reusable vertical-landing boosters

Study           What was varied          Finding                             Source      Confidence Notes
                                                                             type

Dresia et al.,  Engine count 5–15        Optimal RP-1 first stages had 5–6   Peer-       Medium  Doesn’t model a
JSR 2021 (S5)   (first stage), chamber   engines. The authors say the        reviewed            landing throttle limit
                pressure, mixture        optimum “seems to be relatively                         explicitly. Assumes
                ratio, expansion ratio,  small” but that this follows from                       constant landing Δv.
                Δv split; minimum        mass correlations that “only
                acceleration 1.3 g       consider the engine mass as a                            dlr
                                         function of the engine thrust.”

                                          dlr

Stappert et     Propellants, staging,    Hydrocarbon VTVL launchers for      Conference  Medium  Engine count came
al., Space      engine cycle; DLR’s      7.5 t to GTO needed 15–17                               from liftoff T/W, not
Propulsion      generic reusable gas-    engines, which only fit with                            optimization. Deep-
2018 (S6)       generator engines        slight overhang. Hydrogen                               throttle transients
                                         versions needed 9. dlr                                  were not modeled.

                                                                                                  dlr

DLR SART,       Small and large          For small stages, landing T/W       Conference  Medium  Confirms the throttle
IAF 2022 and    reusable stages          “would exceed 3, even with the                          floor sets the
SLME studies                             engine deeply throttled-down to                         minimum engine
(S17)                                    30%.” A reusable engine needs                           size.
                                         33–100% throttling to land at
                                         T/W near 1. dlr dlr

Akin, UMd       Engine-out logic         Picked 6 engines so worst-case      Academic Medium     A simple way to
(S7)                                     acceleration stays positive after                       model engine-out.
                                         losing one: (5/6)·1.3 = 1.083 > 1.

                                          umd

Krevor &        —                        Not retrieved or verified in this —             —       Don’t cite until

Wilhite                                  research                                                checked.

(2007)

Landing T/W check (engineering calculation from published numbers): Assume a landing mass of 27–30 t, so weight is
about 265–295 kN. One Block 5 engine at 57% gives 482 kN, or T/W ≈ 1.6–1.8. That is why Falcon 9 can’t hover and does a
single “hoverslam” burn. ycombinator At a fixed 7,605 kN total, the rated thrust per engine is 7,605/N kN. For T/W ≤ 1 at
minimum throttle, N ≥ about 15–16 at 57% and about 11 at 40%. For DLR’s T/W ≤ 3, N ≥ about 5. These limits cover the range
of published answers (5–6 in Dresia, 9 on Falcon 9, 15–17 in DLR).

Discrepancies Between Sources

  1. Total sea-level thrust: 7,605 kN (S1 text) vs 7,686 kN (S1 Table 2-1, S2) vs 7,607 kN (S5, S13). The cause is 845 vs 854
      kN per engine. mit +2

  2. Liftoff mass: 549,054 kg (official, S3) vs 569.3 t (S5). dlr spacex The 20 t gap means the S5 mass split doesn’t match
      the official total.

  3. First-stage dry mass: 27.2 t (S5) vs 25.6 t (S19) dlr wevolver vs community figures of about 22 t and up. None is
      official.
4. Merlin 1D minimum throttle: 57% (official, Block 5) vs 70% (2013 version, SpaceX statement quoted by
    NASASpaceFlight, S12) vs about 40% (forums).

5. Merlin 1D chamber pressure: 9.7 MPa (S13) vs 10.8 MPa (S19). Wikipedia wevolver
6. Exit diameter: 0.92 m (S13) vs about 1.07 m implied by 0.90 m² exit area (S19). Wikipedia wevolver
7. Reusable LEO payload: more than 17.4 t demonstrated (SpaceX on X, Starlink 5-2, Jan 2023; S16) vs 17.5 t or 18.5 t on

    different Wikipedia pages.
8. Upper-stage vacuum thrust: 934 kN (FT, S13) vs 981 kN (Block 5, official). Wikipedia +3
9. H-1 mass: 635 vs 911 vs about 1,000 kg. RD-180 mass: 5,393 vs 5,480 kg.
Recommendations: Baseline Simulation Inputs

Input                        Baseline                          Range for sensitivity      Basis
                                                                                          Published (S1)
Total sea-level thrust (held 7,605 kN                          —
                                                                                          Published estimate (S5), not official
constant)
                                                                                          Published estimate (S5), not official
Per-engine vacuum thrust     914/845 = 1.082                   1.07–1.10                  Published (S1), plus sensitivity
ratio                                                                                     Secondary (S13, S12)
                                                                                          Engineering assumption
Sea-level / vacuum Isp       283 / 312 s                       ±3 s                       calibrated to S7/S13
                                                                                          Published MER (S7) plus
Minimum throttle             57%                               40–70%                     assumption

Engine T/W at 845 kN         184 (470 kg)                      150–200                    Unofficial (S5, S19)

Engine mass vs thrust        Akin form scaled by 0.56 so it    Exponent 0.8–1.0 on a      Model proxy (S5, S6)
                             matches 470 kg at 845 kN          power-law alternative      Derived from S3 and S5,
                                                                                          assumption
Thrust structure             2.55×10⁻⁴ kg/N × total thrust,    —                          Unofficial (S5); share check (S6)

                             plus a per-engine add-on of 0–50                             Published model value (S5)
                                                                                          Official thrust and burn time (S1,
                             kg                                                           S3); others unofficial (S5)
                                                                                          Assumption from S5 payload-bay
First-stage dry mass (9      26 t                              22–27.2 t                  value
                                                                                          Unofficial proxy (not published)
engines)
                                                                                           orbitalradar
Recovery hardware            12% of dry mass                   8–15%
                                                                                          Assumption, bounded by S14
First-stage propellant       411 t (scaled so GLOW = 549 t) 400–419 t                     telemetry (3.43 g) and S2 limit loads
                                                                                          (6 g)
Landing propellant (drone    25 t                              15–35 t                    Published feasibility threshold
ship)                                                                                     (S17)
                             2,000 m/s                         1,500–2,200 m/s
Landing Δv
                             981 kN / 348 s / 4.5 t / 111.5 t / 397 Isp ±3 s; dry ±0.5 t
Upper stage: thrust / Isp /  s
dry / propellant / burn
                             2.4 t, dropped at about 3 min     1.7–2.6 t
Fairing + adapter

Max-Q limit                  35 kPa                            30–40 kPa

Ascent axial acceleration    4 g steady                        3.4–6 g
cap

Landing T/W cap (single ≤ 3                                    1–3

engine at minimum

throttle)
Input                       Baseline                        Range for sensitivity   Basis
Engine-out rule                                             —                       Published method (S7)
Launch site / target orbit  Positive acceleration with N−1  Inclinations up to 55°
Validation target           engines                         ±5%                     Published (S1, S2)

                            28.56° N (SLC-40); 200 km                               Official (S3) / official (SpaceX on X,
                            circular, 28.5°                                         Starlink 5-2, S16)

                            22,800 kg expendable; more
                            than 17,400 kg drone-ship
                            reusable

What to do: Validate your model at N = 9 against the 22.8 t expendable and about 17.4 t reusable payloads. Then sweep N
from 5 to 27 at fixed 7,605 kN, with the landing T/W cap and throttle floor as active constraints. Report the optimum as a
band across the MER exponent and throttle floor, not as a single number. Based on the calculation above, the binding
constraint at small N is likely landing T/W, and at large N it is per-engine fixed mass plus thrust-structure complexity.

Caveats

      No official SpaceX source gives Falcon 9 stage dry mass, propellant load, landing propellant, Isp, engine mass, max-Q,
      MECO state or touchdown velocity. Every such value here is an estimate and is labeled that way.
      The engine table in E1 came from search snippets collected by a research sub-agent. Primary pages (NASA MSFC F-
      1/H-1 fact sheets, Energomash engine pages) were not opened. Check them before quoting in the abstract.
      The Rohrschneider, Castellini, Tizón & Román and Krevor & Wilhite sources were not retrieved, so their functional
      forms are not given here.
      The landing T/W limits in Section F are engineering calculations from published inputs, not published results.
      Following this report’s format, there is no separate bibliography at the end. The Source Key gives each source’s title,
      author or organization, year and URL or DOI.

```
