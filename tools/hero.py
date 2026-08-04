#!/usr/bin/env python3
"""Build assets/hero.svg — the animated ASCII hero for the profile README.

Left half is a room on a character grid: someone walks in, lowers into the
chair, opens a laptop and starts typing. Right half is the terminal that
window is printing to — open and waiting from the first frame, so the panel
is never an empty box.

Two animation primitives do all the work:

    in(t)      hidden until t, then visible forever   (resting state: visible)
    seg(t, d)  visible only during [t, t+d)           (resting state: hidden)

Because `in` rests visible and `seg` rests hidden, the resting frame of the
whole SVG is the finished scene: seated at the desk, laptop open, readout
printed. A renderer that ignores CSS animation, or a reader with
prefers-reduced-motion, gets that frame instead of a blank card.

    python3 tools/hero.py
"""

from pathlib import Path
from string import Template

# ------------------------------------------------------------------- timeline
# A walk cycle is four poses — contact, down, passing, up — and one cycle
# carries the body exactly one stride, so the planted foot stays put instead
# of skating. STEP is the frame; ADV is how far the body travels per frame.
STEP, STEPS = 0.08, 24         # six cycles, twelve and a half frames a second
T_STOP   = STEPS * STEP          # 1.92  arrives, feet together
SIT_STEP = 0.13
T_SEAT   = T_STOP + 3*SIT_STEP   # 2.31  hips on the chair
T_LID    = T_SEAT + 0.18         # 2.49  hand finds the lid
LID_STEP = 0.13
T_OPEN   = T_LID + 2*LID_STEP    # 2.75  laptop open
T_LIT    = T_OPEN + 0.20         # 2.95  screen on
T_TYPE   = T_LIT + 0.04          # 2.99  hands on the keys
T_CMD    = 3.25                  # command types itself in (0.7s)
T_LOG    = 4.15
T_HEAD   = 4.75
T_DATA   = 5.05                  # readout rows, 0.14s apart
T_DONE   = 6.20
T_PROM   = 6.40

# -------------------------------------------------------------- the ascii grid
# 17 rows of a small room, indexed from the ceiling down:
#
#   0       pendant lamp        6-11   standing body: head, torso, pelvis
#   2-6     window              7-9    laptop lid and screen
#   3-5     poster              7-8    seated head, level with that screen
#   8-16    chair                 10   keyboard deck — where the hands land
#                                 11   desk surface, at the seated waist
#                              13-16   legs; 16 is the floor
#
# Row 10 is the load-bearing one: the shoulders sit a row above it and the
# machine's keys a row below its own lid, so the forearm leaves the shoulder,
# drops one row, and ends on the keys instead of groping past them.
LAMP = ["                         ╭───┴───╮"]
POSTER = ["", "", "",
          "     ┌───────┐",
          "     │ ▁▂▃▂▁ │",
          "     └───────┘"]
# It is night, which is why the pendant is worth switching on and why the
# laptop is the brightest thing in the room.
WINDOW = ["", "",
          "                                        ┌────┬────┐",
          "                                        │    │    │",
          "                                        ├────┼────┤",
          "                                        │    │    │",
          "                                        └────┴────┘"]
PLANT = ["", "", "", "", "", "", "", "", "", "", "", "",
         "                                                 ╲│╱",
         "                                                  │",
         "                                                 ┌─┐",
         "                                                 │ │",
         "                                                 └─┘"]
# the surface shares row 11 with the underside of the laptop, so the machine
# sits on the desk instead of hovering a row above it. The near leg is set in
# to column 24 — at the end of the top it drew a second vertical straight
# through the seated figure, which read as a bar across their chest.
DESK = ["", "", "", "", "", "", "", "", "", "", "",
        "                  ═════════════════════════════",
        "                        ║                     ║",
        "                        ║                     ║",
        "                        ║                     ║",
        "                        ║                     ║",
        "  ──────────────────────╨─────────────────────╨──────"]
# A back tall enough for the seated torso to lean against, a seat the thigh
# lands on, and one post — the chair is pulled up to the desk, so a second
# front leg would just have made stripes against the desk's own.
CHAIR = ["", "", "", "", "", "", "", "", "",
         "            ╭─╮",
         "            │",
         "            │",
         "            │",
         "            ╰─────╮",
         "               │",
         "               │",
         "               ╨"]
# two rows and a handle hung off the right wall, so it reads as a mug and not
# as an orange box someone left on the desk
MUG = ["", "", "", "", "", "", "", "", "", "",
       "                                          ╭─╮╮",
       "                                          ╰─╯╯"]

# laptop lid: closed, cracked, half, open — the base never moves. Two columns
# of overhang past the hinge, not three: any more and the base stops reading as
# a base and starts reading as a shelf someone left the screen on.
LID = [
    ["", "", "", "", "", "", "", "", "", "",
     "                      ┌──────────────┐",
     "                      └──────────────┘"],
    ["", "", "", "", "", "", "", "", "",
     "                        ┌──────────┐",
     "                      ┌─┴──────────┴─┐",
     "                      └──────────────┘"],
    ["", "", "", "", "", "", "", "",
     "                        ┌──────────┐",
     "                        │          │",
     "                      ┌─┴──────────┴─┐",
     "                      └──────────────┘"],
    ["", "", "", "", "", "", "",
     "                        ┌──────────┐",
     "                        │          │",
     "                        │          │",
     "                      ┌─┴──────────┴─┐",
     "                      └──────────────┘"],
]
SCREEN = ["", "", "", "", "", "", "", "",
          "                         % profile",
          "                         ▁▂▄▃▅▇▆▇▅▆"]

SX, SY, SFS = 34, 164, 18                # scene origin / font size
SLH = SFS                                # ascii wants line-height ≈ font-size
SCW = SFS * 0.6


# Twelve rows from crown to floor, and the halves come out even: head and
# torso six, legs six — which is what a human actually measures. A head with
# two rows of mass and shoulders wider than the waist; a bead on a rectangle
# reads as furniture, not a person.
#
#   6-7  head, on a neck stem     9   chest — the arms hang off this row
#   8    shoulders, the widest   10   the taper in to the waist
#        the body gets           11   hips, where the legs split
#
# Shoulders five columns, hips three: the taper is most of what separates a
# person from a filing cabinet. Head two rows against four of torso, which is
# roughly the one-to-two a real head keeps against a real ribcage.
STAND = ["   ╭─╮", "   ╰┬╯", "  ╭─┴─╮", "  │   │", "  ╰╮ ╭╯", "   ╰┬╯"]


def body(drop=0):
    """Head and torso. `drop` lowers it a row and takes the chest out of the
    middle — which is what folding into a chair looks like on a grid: the
    shoulders and hips keep their shape, the height between them closes."""
    f = [""] * 17
    for i, s in enumerate(STAND if not drop else STAND[:3] + STAND[4:]):
        f[6 + drop + i] = s
    return f


def figure(legs, arm=()):
    """The standing body, then whatever legs and arm the pose calls for."""
    f = body()
    for r, s in tuple(arm) + tuple(legs):
        f[r] = s
    return f


# One stride is four columns, so the body advances one column a frame and the
# support foot walks back through the pose at exactly the same rate — 6 at
# heel strike, then 5, 4, 3, and 2 at the next contact, where it has become
# the trailing foot and has not moved an inch in room coordinates.
CONTACT = [(12, "   ╱ ╲"), (13, "  ╱   ╲"), (14, "  │   │"),
           (15, "  │   │"), (16, "  ┴   ┴")]
DOWN    = [(12, "   ╱╲"), (13, "  ╱  ╲"), (14, "  │  │"),
           (15, "  │  │"), (16, "  ╵  ┴")]
PASSING = [(12, "    │╲"), (13, "    │ ╵"), (14, "    │"),
           (15, "    │"), (16, "    ┴")]
PUSHOFF = [(12, "   ╱╲"), (13, "   │ ╲"), (14, "   │  │"),
           (15, "   │  ╵"), (16, "   ┴")]

# The hips ride highest at passing and lowest at down. Two or three pixels is
# all it takes; more and the planted foot visibly leaves the floor.
WALK = [(CONTACT, 0), (DOWN, 2), (PASSING, -3), (PUSHOFF, -1)]

# The near arm swings against the near leg, so it takes two steps — eight
# poses — to come back to where it started. Two diagonal cells chain corner to
# corner into a straight arm; at the mid-swing the arm is passing the body and
# foreshortens to one. Each pose redraws the torso rows it crosses so the
# overlay never punches a hole in the chest.
# The arm takes over the torso edge it covers, so the two cells chain off the
# shoulder's own descender instead of floating a column clear of it.
A_BACK2 = [(9, "  ╱   │"), (10, "╱ ╰╮ ╭╯")]
A_BACK1 = [(9, "  ╱   │")]
A_FWD1  = [(9, "  │   ╲")]
A_FWD2  = [(9, "  │   ╲"), (10, "  ╰╮ ╭╯╲")]
ARMS = [A_BACK2, A_BACK1, A_FWD1, A_FWD2,
        A_FWD2,  A_FWD1,  A_BACK1, A_BACK2]

# Three frames between the last footfall and the hips landing: feet together,
# knees bending as the hips drop, then the thigh swinging forward to the seat.
SIT = [
    (0, [(12, "    │"), (13, "    │"), (14, "   ╱ ╲"),
         (15, "   │ │"), (16, "   ┴ ┴")]),
    (1, [(12, "   ╱╲"), (13, "   │ ╲"), (14, "   │  │"),
         (15, "   │  │"), (16, "   ┴  ┴")]),
    (1, [(12, "    ╰─╮"), (13, "      ╰─╮"), (14, "        │"),
         (15, "        │"), (16, "        ╰─")]),
]

# Sitting folds the legs, not the spine: the torso keeps its height, the head
# drops to screen level, the thigh runs forward along the seat and the shin
# falls into the knee-hole under the desk. Rows 9 and 10 are left out on
# purpose — an arm layer always supplies them, so the forearm can leave the
# chest without a leftover torso line showing through it.
SEATED = ["", "", "", "", "", "", "", "", "", "", "",
          "  ╰╮ ╭╯", "   ╰┬╯",
          "    ╰───╮", "        │", "        │", "        ╰─"]
HEAD = ["", "", "", "", "", "", "", "   ╭─╮", "   ╰┬╯"]

# Seated, the shoulder opens into the arm that works the machine. The forearm
# leaves the shoulder's own descender, drops to row 10 and runs out along the
# keyboard deck, so it ends on the machine rather than beside it — the hand is
# the ┬, a line with a finger on it. Reach goes two columns further out, onto
# the lid it is about to lift; typing pulls back and the hand travels one
# column, which at this scale is a hand moving across keys and not an arm
# growing. Both poses cover column 22, so the base's near corner never blinks.
REACH  = [(9, "  ╭─┴─╮"), (10, "  │   ╰─────┬")]
TYPE_A = [(9, "  ╭─┴─╮"), (10, "  │   ╰───┬")]
TYPE_B = [(9, "  ╭─┴─╮"), (10, "  │   ╰────┬")]

# ------------------------------------------------------------ terminal readout
TX, TY, TW, TH = 618, 48, 550, 440
BAR = 32                                 # title bar height
CW  = 7.83                               # advance of the 13px terminal font
CL  = TX + 22                            # left text margin
COL = CL + 10*CW                         # colon column
CV  = CL + 12*CW                         # value column


def line(n):
    """Terminal text baseline for row n of the 20px line grid."""
    return TY + BAR + 30 + n*20


ROWS = [
    ("Role",      "Software Engineer"),
    ("Focus",     None),
    # ("Building",  "developer tools, cloud platforms, fast inference"),
    ("Stack",     "Python, C++, CUDA, Triton, PyTorch, AWS"),
    ("Education", "MS Computer Science, Arizona State University"),
    ("Experience",    "Former Co-Founder | Founding Engineer at SharpData"),
    ("Status",    "open to interesting problems"),
]
FOCUS = ["AI systems", "cloud infrastructure", "accelerated computing", "product engineering"]
LOGS  = [("reading profile", 0)]
CMD   = "./profile.sh"
NAME  = "Varad More"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def art(rows, cls, fill, dx=0, dy=0, style=""):
    """One layer of the scene grid: a <text> of absolutely placed tspans."""
    spans = "".join(f'<tspan x="{SX}" y="{SY + r*SLH}">{esc(s)}</tspan>'
                    for r, s in enumerate(rows) if s.strip())
    shift = f' transform="translate({dx:.1f} {dy})"' if (dx or dy) else ""
    style = f' style="{style}"' if style else ""
    return f'    <text class="art {cls}" xml:space="preserve" fill="{fill}"{shift}{style}>{spans}</text>'


def seg(t, d):
    return f"animation-delay:{t:.2f}s;animation-duration:{d:.2f}s"


FIG   = "#C4B5FD"
LITF  = "#E9DDFF"        # the same figure, once the screen is lighting it
ROOM  = "#4E5D70"
ROOM2 = "#3B4757"

SEAT = 12 * SCW          # the chair, in scene columns
ADV  = SCW               # body travel per walk frame — a quarter stride a pose

# Two lights, and both of them arrive with the person: the pendant they switch
# on at the door, and the laptop that catches their face once it opens.
LAMPX  = SX + 29.5*SCW   # centre of the shade
LAMPY  = SY + 6          # its underside
FLOORY = SY + 16*SLH     # the floor line
CONE   = (f"{LAMPX-22:.0f},{LAMPY} {LAMPX+22:.0f},{LAMPY} "
          f"{LAMPX+152:.0f},{FLOORY + 4} {LAMPX-152:.0f},{FLOORY + 4}")
MUGX   = SX + 43*SCW     # steam rises off the mug from here
WINX, WINY = int(SX + 40.4*SCW), SY + 2*SLH - 13


def walk_in():
    """Six cycles of the four poses, ending at the chair."""
    out = []
    for i in range(STEPS):
        legs, bob = WALK[i % 4]
        x = SEAT - (STEPS - 1 - i) * ADV
        out.append(art(figure(legs, arm=ARMS[i % 8]), "seg fig",
                       FIG, dx=x, dy=bob, style=seg(i*STEP, STEP)))
    return "\n".join(out)


def sit_down():
    """Three frames between the last footfall and the hips landing."""
    out = []
    for i, (drop, legs) in enumerate(SIT):
        f = body(drop)
        for r, s in legs:
            f[r] = s
        out.append(art(f, "seg fig", FIG, dx=SEAT,
                       style=seg(T_STOP + i*SIT_STEP, SIT_STEP)))
    return "\n".join(out)


def laptop():
    return "\n".join([
        art(LID[0], "seg", ROOM, style=seg(0, T_LID)),
        art(LID[1], "seg", ROOM, style=seg(T_LID, LID_STEP)),
        art(LID[2], "seg", ROOM, style=seg(T_LID + LID_STEP, LID_STEP)),
        art(LID[3], "in",  ROOM, style=f"animation-delay:{T_OPEN:.2f}s")])


def arm(pose, cls, style="", fill=None):
    """Shoulders and the arm leaving them — the seated figure's top two rows."""
    f = [""] * 17
    for r, s in pose:
        f[r] = s
    return art(f, cls + " fig", fill or FIG, dx=SEAT, style=style)


def readout():
    out = []
    for i, (label, value) in enumerate(ROWS):
        y, delay = line(7 + i), T_DATA + 0.14*i
        out.append(f'      <g class="in" style="animation-delay:{delay:.2f}s">')
        out.append(f'        <text x="{CL}" y="{y}" class="dim">{label}</text>'
                   f'<text x="{COL:.0f}" y="{y}" class="dim">:</text>')
        if value is None:
            for k, t in enumerate(FOCUS):
                out.append(f'        <text x="{CV:.0f}" y="{y}" class="focus f{k+1}" fill="#A78BFA">{t}</text>')
        elif label == "Status":
            out.append(f'        <circle class="halo" cx="{CV+5:.0f}" cy="{y-4}" r="3.5" fill="#3FB950"/>'
                       f'<circle cx="{CV+5:.0f}" cy="{y-4}" r="3.5" fill="#3FB950"/>'
                       f'<text x="{CV+20:.0f}" y="{y}" fill="#7EE787">{value}</text>')
        else:
            out.append(f'        <text x="{CV:.0f}" y="{y}" fill="#E6EDF3">{value}</text>')
        out.append('      </g>')
    return "\n".join(out)


def ok(msg, y, delay):
    return (f'      <g class="in" style="animation-delay:{delay:.2f}s">'
            f'<text x="{CL}" y="{y}" fill="#3FB950">[<tspan fill="#7EE787"> ok </tspan>]</text>'
            f'<text x="{CL+52:.0f}" y="{y}" class="dim">{msg}</text></g>')


def logs():
    return "\n".join(ok(msg, line(2 + i), T_LOG + 0.26*i) for msg, i in LOGS)


def prompt(y):
    return (f'<text x="{CL}" y="{y}" fill="#7EE787">varad<tspan class="dim">@</tspan>more'
            f'<tspan class="dim"> ~ </tspan><tspan fill="#A78BFA">%</tspan></text>')


SVG = Template('''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="540" viewBox="0 0 1200 540" fill="none" role="img" aria-labelledby="heroTitle heroDesc">
  <title id="heroTitle">varad@more — Software Engineer</title>
  <desc id="heroDesc">An ASCII scene: someone walks to a desk, sits down, opens a laptop and runs a script, and the terminal window beside them prints the profile of Varad More, a software engineer working on AI systems, accelerated computing, cloud infrastructure and product engineering.</desc>

  <defs>
    <radialGradient id="aurora">
      <stop offset="0%" stop-color="#7C5CFF" stop-opacity="0.20"/><stop offset="100%" stop-color="#7C5CFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="cool">
      <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.12"/><stop offset="100%" stop-color="#22D3EE" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="screenGlow">
      <stop offset="0%" stop-color="#8B7BFF" stop-opacity="0.42"/><stop offset="100%" stop-color="#7C5CFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="bulb">
      <stop offset="0%" stop-color="#FFCE8A" stop-opacity="0.30"/><stop offset="100%" stop-color="#FFCE8A" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FFC078" stop-opacity="0.14"/><stop offset="55%" stop-color="#FFC078" stop-opacity="0.04"/><stop offset="100%" stop-color="#FFC078" stop-opacity="0"/>
    </linearGradient>
    <filter id="soft" x="-40%" y="-25%" width="180%" height="150%">
      <feGaussianBlur stdDeviation="16"/>
    </filter>
    <linearGradient id="night" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#101B33"/><stop offset="100%" stop-color="#1B2440"/>
    </linearGradient>
    <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#B9C6FF" stop-opacity="0.05"/><stop offset="100%" stop-color="#B9C6FF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#05070B"/><stop offset="100%" stop-color="#05070B" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2A323F"/><stop offset="100%" stop-color="#181F28"/>
    </linearGradient>
    <!-- the card is a room photographed, not a swatch: light off the top,
         weight at the bottom, and the corners falling away -->
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#111624"/><stop offset="55%" stop-color="#0B0E14"/><stop offset="100%" stop-color="#07090E"/>
    </linearGradient>
    <radialGradient id="vignette" cx="50%" cy="46%" r="72%">
      <stop offset="55%" stop-color="#000000" stop-opacity="0"/><stop offset="100%" stop-color="#000000" stop-opacity="0.55"/>
    </radialGradient>
    <!-- the terminal's own glass: a lit panel, brightest just under the bar -->
    <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#141A23"/><stop offset="30%" stop-color="#0D1119"/><stop offset="100%" stop-color="#080B10"/>
    </linearGradient>
    <radialGradient id="termGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#4E7BFF" stop-opacity="0.16"/><stop offset="100%" stop-color="#4E7BFF" stop-opacity="0"/>
    </radialGradient>
    <filter id="drop" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="20" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
    <clipPath id="card"><rect width="1200" height="540" rx="16"/></clipPath>
  </defs>

  <style>
    text { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 13px }
    .dim { fill: #6E7681 }
    .sm  { font-size: 12px }
    .art { font-size: ${SFS}px }
    /* the figure carries a little stroke weight so it reads as the subject
       and the room stays line art behind it */
    .fig { stroke: ${FIG}; stroke-width: .8 }
    .litfig { stroke: ${LITF} }

    /* hidden until its delay, then visible for good */
    @keyframes in { from { opacity: 0 } to { opacity: 1 } }
    .in  { animation: in .3s cubic-bezier(.16,1,.3,1) both }
    /* visible only for its own slice of the timeline */
    @keyframes seg { 0%, 100% { opacity: 1 } }
    .seg { opacity: 0; animation-name: seg; animation-timing-function: step-end; animation-iteration-count: 1 }

    .lit    { animation: in .5s ${T_LIT}s backwards }
    .hands  { animation: in .01s ${T_TYPE}s backwards }

    /* seated, then lit: the screen coming on is what warms the figure, so the
       fill animates on the same element rather than fading in a second copy */
    .body { animation: in .01s ${T_SEAT}s backwards, litup .9s ${T_LIT}s both }
    @keyframes litup { to { fill: ${LITF}; stroke: ${LITF} } }

    /* a head that never moves is a mannequin. Down to the keys, back up to
       the screen — two pixels, on the `translate` property so it composes
       with the transform attribute that put the figure at the chair. */
    .nod { animation: in .01s ${T_SEAT}s backwards, litup .9s ${T_LIT}s both,
                      nod 7s ${T_TYPE}s ease-in-out infinite }
    @keyframes nod { 0%, 40%, 100% { translate: 0 0 } 55%, 75% { translate: 0 2px } }

    /* the pendant, switched on at the door — one flicker, then steady */
    .lamp { animation: lamp .6s ${T_STOP}s both }
    @keyframes lamp { 0%, 20% { opacity: 0 } 30% { opacity: 1 } 42% { opacity: .2 } 100% { opacity: 1 } }

    @keyframes steam { 0% { opacity: 0; transform: translateY(7px) } 30% { opacity: .5 } 100% { opacity: 0; transform: translateY(-17px) } }
    .steam  { opacity: 0; animation: steam 4.6s ease-out infinite }
    .steam2 { animation-delay: 2.3s }

    /* fingers working, once the hands are on the keys */
    @keyframes flip { 0% { opacity: 1 } 50%, 100% { opacity: 0 } }
    .ha { animation: flip .8s step-end ${T_TYPE}s infinite }
    .hb { opacity: 0; animation: flip .8s step-end ${T_TYPE_B}s infinite }

    /* the command types in one character at a time. Both ends of the keyframe
       are inset() over the text's own box, so it interpolates cleanly and the
       resting state — animation off — is the whole line, already run. */
    .type { clip-path: inset(-30% -6% -30% 0); animation: type .7s steps(${CMDN}) ${T_CMD}s backwards }
    @keyframes type { from { clip-path: inset(-30% 100% -30% 0) } }

    .focus { opacity: 0; animation: focus 14s step-end ${T_DATA}s infinite }
    .f1 { opacity: 1 }
    .f2 { animation-delay: ${F2}s } .f3 { animation-delay: ${F3}s } .f4 { animation-delay: ${F4}s }
    @keyframes focus { 0% { opacity: 1 } 25%, 100% { opacity: 0 } }

    .halo { transform-origin: ${HALOX}px ${HALOY}px; animation: halo 2.6s ease-out ${T_PROM}s infinite }
    @keyframes halo { 0% { transform: scale(.6); opacity: .8 } 100% { transform: scale(2.8); opacity: 0 } }

    .caret { animation: caret 1.1s steps(1) infinite }
    @keyframes caret { 0%, 50% { opacity: 1 } 51%, 100% { opacity: 0 } }
    .caret2 { animation: in .01s ${T_PROM}s backwards, caret 1.1s steps(1) ${T_PROM}s infinite }

    .glow { animation: in 1.4s ${T_LIT}s backwards, breathe 5s ${T_LIT}s ease-in-out infinite }
    @keyframes breathe { 0%, 100% { opacity: .7 } 50% { opacity: 1 } }

    @media (prefers-reduced-motion: reduce) {
      .in, .lit, .body, .nod, .hands, .halo, .caret, .caret2,
      .glow, .ha, .hb, .lamp, .steam { animation: none }
      .body { fill: ${LITF}; stroke: ${LITF} }
      .steam { opacity: 0 }
      .type { animation: none; clip-path: none }
      .seg { animation: none; opacity: 0 }
      .hb, .halo { opacity: 0 }
      .focus { animation: none; opacity: 0 } .f1 { opacity: 1 }
    }
  </style>

  <g clip-path="url(#card)">
    <rect width="1200" height="540" fill="url(#sky)"/>
    <ellipse cx="330" cy="330" rx="400" ry="270" fill="url(#aurora)"/>
    <ellipse cx="900" cy="150" rx="460" ry="320" fill="url(#cool)"/>

    <!-- left: the room, after dark -->
    <rect x="${WINX}" y="${WINY}" width="${WINW}" height="${WINH}" fill="url(#night)"/>
    <g fill="#FFD9A8" fill-opacity="0.5">$CITY</g>
$WINDOW
    <rect y="${FLOORY}" width="620" height="${FLOORH}" fill="url(#floor)"/>

    <g class="lamp">
      <polygon points="${CONE}" fill="url(#beam)" filter="url(#soft)"/>
      <ellipse cx="${LAMPX}" cy="${LAMPY}" rx="58" ry="17" fill="url(#bulb)"/>
    </g>
    <line x1="${CORDX}" y1="0" x2="${CORDX}" y2="${CORDY}" stroke="${ROOM}" stroke-width="1.2"/>
$LAMP
$POSTER
$DESK
$PLANT
$CHAIR
$MUG
    <text class="steam sm" x="${MUGX}" y="${STEAMY}" fill="#8A8FA0" xml:space="preserve">~</text>
    <text class="steam steam2 sm" x="${MUGX2}" y="${STEAMY}" fill="#8A8FA0" xml:space="preserve">~</text>

    <ellipse class="glow" cx="${GLOWX}" cy="${GLOWY}" rx="130" ry="58" fill="url(#screenGlow)"/>
$LAPTOP
    <g class="lit">
$SCREEN
      <rect class="caret" x="${SCRCX}" y="${SCRCY}" width="9" height="14" fill="#7EE787" fill-opacity="0.85"/>
    </g>

$WALKIN
$SITDOWN
$BODY
$HEAD
$REACH
    <g class="hands">
$TYPE_A
$TYPE_B
    </g>
    <rect width="96" height="540" fill="url(#edge)"/>
    <rect width="1200" height="540" fill="url(#vignette)"/>

    <!-- right: the terminal it is printing to -->
    <g>
      <ellipse cx="${TMID}" cy="${TCY}" rx="380" ry="290" fill="url(#termGlow)"/>
      <g filter="url(#drop)">
        <path d="M${TX} ${TB}v${BODYH}a10 10 0 0 0 10 10h${INNERW}a10 10 0 0 0 10 -10v-${BODYH}z" fill="url(#glass)" fill-opacity="0.97"/>
        <path d="M${TX} ${TB}v-${BARH}a10 10 0 0 1 10 -10h${INNERW}a10 10 0 0 1 10 10v${BARH}z" fill="url(#bar)"/>
      </g>
      <path d="M${TX} ${TB}h${TW}" stroke="#05070B" stroke-opacity="0.9"/>
      <path d="M${TXR} ${TYT}h${INNERW}" stroke="#FFFFFF" stroke-opacity="0.14"/>
      <rect x="${TXH}" y="${TYH}" width="${TW}" height="${TH}" rx="10" fill="none" stroke="#FFFFFF" stroke-opacity="0.09"/>
      <g stroke="#000000" stroke-opacity="0.16">
        <circle cx="${DOT1}" cy="${DOTY}" r="5.5" fill="#FF5F57"/><circle cx="${DOT2}" cy="${DOTY}" r="5.5" fill="#FEBC2E"/><circle cx="${DOT3}" cy="${DOTY}" r="5.5" fill="#28C840"/>
      </g>
      <text x="${TMID}" y="${DOTT}" class="dim sm" text-anchor="middle">varad@more — -zsh — 64×20</text>

      <g>
        $PROMPT0
        <text class="type" x="${CMDX}" y="${CMDY}" fill="#E6EDF3">${CMD}</text>
        <g class="seg" style="animation-delay:0s;animation-duration:${T_CMD}s">
          <rect class="caret" x="${CMDX}" y="${CARETY0}" width="8" height="15" fill="#E6EDF3"/>
        </g>
      </g>

$LOGS

      <g class="in" style="animation-delay:${T_HEAD}s">
        <text x="${CL}" y="${HEADY}" font-weight="700" fill="#E6EDF3">${NAME}<tspan fill="#30363D" font-weight="400"> ${RULE}</tspan></text>
      </g>

$READOUT

$DONE
      <g class="in" style="animation-delay:${T_PROM}s">$PROMPT1</g>
      <rect class="caret2" x="${CARETX}" y="${CARETY}" width="8" height="15" fill="#E6EDF3"/>
    </g>
  </g>
  <rect x="0.5" y="0.5" width="1199" height="539" rx="16" fill="none" stroke="#FFFFFF" stroke-opacity="0.09"/>
</svg>
''')

CMDX = CL + 15*CW
svg = SVG.substitute(
    SFS=SFS, ROOM=ROOM, FIG=FIG, LITF=LITF,
    T_LIT=T_LIT, T_CMD=T_CMD, T_HEAD=T_HEAD, T_DATA=T_DATA, T_PROM=T_PROM,
    T_SEAT=T_SEAT, T_TYPE=T_TYPE, T_TYPE_B=T_TYPE + 0.4, T_STOP=T_STOP,
    F2=T_DATA + 3.5, F3=T_DATA + 7, F4=T_DATA + 10.5,
    CMD=CMD, NAME=NAME, CMDN=len(CMD), CMDX=f"{CMDX:.0f}",
    RULE="─" * 53,
    GLOWX=f"{SX + 29.5*SCW:.0f}", GLOWY=SY + 8*SLH,
    CORDX=f"{SX + 29.4*SCW:.0f}", CORDY=SY - 14,
    CONE=CONE, LAMPX=f"{LAMPX:.0f}", LAMPY=LAMPY,
    FLOORY=FLOORY, FLOORH=540 - FLOORY,
    WINX=WINX, WINY=WINY, WINW=110, WINH=88,
    CITY="".join(f'<circle cx="{WINX+dx}" cy="{WINY+dy}" r="{r}"/>'
                 for dx, dy, r in [(22, 64, 1.3), (47, 71, 1), (72, 59, 1.5), (89, 68, 1.1)]),
    WINDOW=art(WINDOW, "", ROOM2),
    MUGX=f"{MUGX:.0f}", MUGX2=f"{MUGX + 6:.0f}", STEAMY=SY + 9*SLH + 10,
    SCRCX=f"{SX + 34*SCW:.0f}", SCRCY=SY + 8*SLH - 12,
    LAMP=art(LAMP, "", ROOM),
    POSTER=art(POSTER, "", ROOM2),
    DESK=art(DESK, "", ROOM),
    PLANT=art(PLANT, "", "#3F7A55"),
    CHAIR=art(CHAIR, "", ROOM),
    MUG=art(MUG, "", "#F0883E"),
    LAPTOP=laptop(),
    SCREEN=art(SCREEN, "", "#7EE787"),
    WALKIN=walk_in(),
    SITDOWN=sit_down(),
    BODY=art(SEATED, "body", FIG, dx=SEAT),
    HEAD=art(HEAD, "body nod", FIG, dx=SEAT),
    REACH=arm(REACH, "seg", style=seg(T_SEAT, T_TYPE - T_SEAT)),
    TYPE_A=arm(TYPE_A, "ha litfig", fill=LITF),
    TYPE_B=arm(TYPE_B, "hb litfig", fill=LITF),
    TX=TX, TW=TW, TH=TH, TB=TY + BAR, TMID=TX + TW // 2, BARH=BAR - 10,
    TCY=TY + TH // 2,
    TXH=TX + 0.5, TYH=TY + 0.5, TXR=TX + 10, TYT=TY + 0.5,
    INNERW=TW - 20, BODYH=TH - BAR - 10,
    DOT1=TX + 21, DOT2=TX + 41, DOT3=TX + 61, DOTY=TY + 17, DOTT=TY + 21,
    CL=CL, LOGS=logs(), READOUT=readout(),
    DONE=ok("EOF", line(14), T_DONE),
    PROMPT0=prompt(line(0)), PROMPT1=prompt(line(15)),
    HALOX=f"{CV+5:.0f}", HALOY=line(7 + [r[0] for r in ROWS].index("Status")) - 4,
    CMDY=line(0), HEADY=line(5), CARETY0=line(0) - 12,
    CARETX=f"{CL + 15*CW:.0f}", CARETY=line(15) - 12,
)

out = Path(__file__).resolve().parents[1] / "assets" / "hero.svg"
out.write_text(svg)
print(f"wrote {out} ({len(svg)} bytes)")
