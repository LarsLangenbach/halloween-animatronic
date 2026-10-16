# Project Brief: Frankenstein Conversational Animatronic
## Mechanical Skull, Eyebrow Mechanisms & Silicone Skin Integration

> Received 2026-10-14. This is the brief as written; it is not edited as the
> design develops. Gaps, decisions and answers are tracked in
> [PLAN.md](PLAN.md), and progress in [BUILD_LOG.md](BUILD_LOG.md).

**Project Type:** Animatronic character / mechanical product design / 3D modeling  
**Character:** Frankenstein-inspired, almost-human monster  
**Primary Fabrication:** FDM 3D printing, silicone casting, mechanical assembly  
**CAD Platform:** Onshape preferred; STEP export compatibility required

---

## 1. Project Overview

We are developing a life-size, conversational animatronic head designed to resemble a Frankenstein-inspired human monster preserved inside a laboratory specimen jar.

The character will be capable of holding natural conversations with visitors, making eye contact, blinking, articulating its mouth during speech, and expressing emotions through its eyebrows and facial movements.

The head will feature a sculpted, flexible silicone skin over an internal 3D-printed mechanical skull.

We intend to reuse two existing open-source mechanisms designed by **Will Cogley**:

- His multi-servo animatronic mouth mechanism.
- His EyeMech ε3.2 eye and eyelid mechanism.

The primary objective of this design project is to create a **custom, mechanically integrated skull and eyebrow actuation system** that supports these existing mechanisms while accommodating the full silicone fabrication, assembly, and maintenance process.

This is not simply a static skull model. It must function as the structural foundation for an expressive animatronic character.

## 2. Design Objectives

The finished mechanical assembly should:

1. Integrate Will Cogley's existing mouth mechanism without unnecessarily redesigning it.
2. Integrate Will Cogley's EyeMech ε3.2 assembly.
3. Incorporate two independently actuated eyebrows using MG90S servos.
4. Support a flexible silicone facial skin that can deform naturally.
5. Provide reliable, removable connections between the silicone skin and moving facial linkages.
6. Allow access to servos, wiring, and mechanical components for maintenance.
7. Establish accurate facial proportions that can be used for sculpting, mold-making, and silicone casting.
8. Minimize unnecessary hardware, assembly complexity, and custom electronics.
9. Be fabricated primarily using in-house 3D printers and readily available mechanical components.
10. Fit inside a future transparent specimen enclosure, with the head mounted on a stable internal support.

## 3. Existing Mechanisms

### A. Mouth Assembly — Will Cogley

We plan to reuse Will Cogley's mouth mechanism with:

- 8 × MG90S micro servos
- 2 × MG996R high-torque jaw servos

**Total: 10 servos**

The existing assembly should be imported into the new skull CAD, maintaining its original mounting dimensions, moving joints, servo clearances, and mechanical articulation wherever possible.

The designer should identify:

- Main attachment points between the mouth assembly and skull.
- Jaw pivot axis and total movement envelope.
- Lip articulation endpoints.
- Mechanical interference during full jaw opening.
- Locations where the silicone skin will attach to moving mouth linkages.
- Clearance for servo maintenance and wire routing.

The mouth assembly must remain removable as a module.

### B. Eye Assembly — Will Cogley's EyeMech ε3.2

Reference CAD:  
https://www.printables.com/model/1220172-animatronic-eye-mechanism-e31/files

GitHub:  
https://github.com/will-cogley/EyeMech_Epsilon

The selected version uses six MG90S servos for:

- Horizontal eye movement
- Vertical eye movement
- Left upper eyelid
- Left lower eyelid
- Right upper eyelid
- Right lower eyelid

**Total: 6 servos**

The eye assembly should be integrated as a complete module within the upper portion of the skull.

Critical requirements:

- Correct alignment of the eyeballs with the sculpted eye sockets.
- Sufficient space for full eye movement and blinking.
- Clearance between eyelids and the surrounding silicone skin.
- A removable mounting frame.
- Accessible fasteners and servo cables.
- Adjustable mounting or shim provisions for fine-tuning eye depth and alignment.

We may need to design separate silicone-covered eyelid surfaces that move with the eye mechanism rather than relying on the main facial skin to form the complete moving eyelids.

## 4. Custom Eyebrow Mechanism

This is one of the primary new mechanical design tasks.

We need two independently articulated eyebrows, each driven by one MG90S servo.

**Total: 2 servos**

### Desired Movement

Each eyebrow should support:

- Raising
- Lowering
- Neutral/rest position
- Expressive asymmetry between left and right sides

The movement should deform the overlying silicone skin convincingly rather than simply rotating a visibly rigid eyebrow component.

### Proposed Mechanical Solution

We propose a compact pivot-driven eyebrow mechanism consisting of:

- One MG90S servo per eyebrow.
- A short servo horn or crank.
- A mechanically supported eyebrow carrier.
- A curved brow contact structure beneath the silicone.
- A small removable attachment interface between the carrier and silicone skin.

The brow carrier should distribute movement across a region of silicone rather than pull at a single highly concentrated point.

The mechanism should fit above the eye assembly without interfering with eyelid movement.

### Specific Design Considerations

- Allow adjustment of the eyebrow's neutral position.
- Minimize unnecessary stretching of the silicone.
- Avoid visible hard points beneath thin skin.
- Keep the mechanism compact within the forehead.
- Design the moving carriers as replaceable 3D-printed components.
- Explore alternative pivot positions or short connecting links if direct servo rotation produces unnatural motion.
- Include adjustable mechanical motion limits to prevent overextending the silicone.

The eyebrow system should be prototyped and tested before finalizing the skull geometry.

## 5. Internal Skull Architecture

The internal skull will be a custom 3D-printed structural framework.

It should be designed around the existing mechanical assemblies rather than attempting to force those assemblies into an independently modeled anatomical skull.

### Proposed Structure

**Upper skull module**
- Supports the complete EyeMech assembly.
- Houses two eyebrow actuators and carriers.
- Provides a forehead/temple structure.
- Includes silicone skin attachment features.

**Lower facial module**
- Houses Cogley's mouth assembly.
- Supports jaw articulation and facial motion.
- Includes skin attachment interfaces around the cheeks, lips, and chin.

**Rear skull structure**
- Supports the upper and lower modules.
- Provides a removable access panel.
- Includes attachment locations for the silicone skin.
- Provides cable routing and attachment points for the main mounting structure.

**Neck/base interface**
- Holds the head rigidly in the enclosure.
- Provides a concealed route for wiring.
- Transfers mechanical loads into the enclosure base.

The design does not currently require motorized neck motion.

### Skull Design Requirements

The skull should:

- Be split into printable, serviceable components.
- Use accessible screws and heat-set inserts where appropriate.
- Be sufficiently rigid to maintain alignment under servo loads.
- Avoid sharp edges in areas contacting the silicone.
- Provide mounting points for silicone skin registration.
- Include internal cable-management channels.
- Allow removal and replacement of individual servos.
- Minimize support material and difficult print orientations.
- Include clearance for servo horns, linkages, and fastener heads throughout their full movement.

## 6. Silicone Face and Attachment System

We intend to sculpt the character's face, create a negative mold, and cast a flexible silicone skin.

The silicone material is currently being evaluated, with Ecoflex 00-30 and PlatSil Gel-OO30 under consideration.

The mechanical design must anticipate this casting process.

### Proposed Skin Attachment Method

We favor a **miniature snap-based attachment system**, inspired by an earlier version of the Cogley mechanism in which facial attachment points used magnets.

The intent is to preserve the compactness and removability of that system while providing more positive mechanical retention.

### Moving Attachment Points

For the lips and eyebrows, we propose:

1. Small fabric reinforcement pads embedded in the silicone during casting.
2. Miniature sew-on metal snaps mechanically stitched to those pads.
3. The fabric and stitching encapsulated within locally reinforced regions of silicone.
4. The mating snap half secured to a small 3D-printed linkage adapter.
5. Individual attachment points that can be connected and disconnected during servicing.

A nominal 7 mm snap diameter is proposed for initial testing, but the final size and engagement force must be validated against the actual linkage dimensions and silicone strength.

The snap's mating surfaces must remain free from silicone during casting.

Snap orientation is critical. The mechanism must be designed so normal facial movement does not repeatedly pull the snap in its release direction.

The design should also include a method for supporting the reinforced skin while disconnecting the snap, so the silicone is not damaged during maintenance.

### Fixed Skin Attachments

The non-moving portions of the skin require stable registration to the skull.

Potential solutions include:

- A reinforced silicone perimeter flange.
- Small hidden mounting tabs.
- Low-profile clips or snap attachments at the rear skull.
- Short removable clamping strips in non-moving areas.

The final design should use fixed attachment locations that maintain skin alignment without preventing the cheeks, lips, chin, and brows from deforming.

### Critical Principle

**The silicone skin must not be permanently glued across the entire rigid skull.**

Only specific fixed areas and active motion interfaces should be attached. The remaining skin must have sufficient freedom to stretch and return to its neutral shape.

## 7. Skin Sculpting and Mold-Making Compatibility

The mechanical CAD will also support the physical sculpture and silicone fabrication process.

Our planned workflow is:

1. Import and position the mouth and eye mechanisms.
2. Design the eyebrow system.
3. Establish a complete digital skull and approximate outer face proportions.
4. 3D-print the mechanical skull and verify the moving assemblies.
5. Produce a sculpting armature or registered face form.
6. Sculpt Frankenstein-inspired facial anatomy using sulfur-free oil-based clay.
7. Create a rigid sectional negative mold of the sculpt.
8. Cast a hollow silicone skin with reinforced attachment areas.
9. Fit the silicone skin onto the mechanical skull.
10. Attach moving skin regions using the miniature snap interfaces.
11. Tune the skin deformation and mechanism motion.

### Important CAD Considerations

The designer must account for the **thickness of the silicone skin between the outer sculpted surface and the internal mechanical skull**.

The skull should not simply follow the surface of the sculpture exactly.

Instead, it needs appropriate relief and support for the silicone thickness, facial deformation, and active mechanisms.

We would like the CAD to help establish:

- Eye socket alignment.
- Mouth and jaw registration.
- Facial centerline and symmetry references.
- Approximate skin thickness zones.
- Internal skull clearances.
- Mold registration features.
- Attachment point coordinates.
- Sculpting armature dimensions.

Where possible, the mechanical skull and sculpting armature should share a common coordinate system so the final silicone skin registers accurately to the servos.

## 8. Appearance and Character Direction

The character is a Frankenstein-inspired, almost-human monster.

The facial design should retain recognizable human anatomy but incorporate unsettling, constructed features.

Possible design characteristics include:

- Heavy, expressive brow ridges.
- Pale gray-green or desaturated flesh tones.
- Subtle asymmetry in facial proportions.
- Prominent, realistic eyes.
- An expressive mouth with convincing lip movement.
- Sculpted seams, scars, or stitching.
- A slightly unnatural skull silhouette.

The design should prioritize expressiveness over extreme facial distortion.

The mouth must remain capable of forming convincing speech shapes, and the brow region must have enough flexible surface area to produce visible expressions.

Cosmetic stitching and raised details should not obstruct moving skin regions.

## 9. Fabrication Constraints

We have access to FDM 3D printers and standard workshop tools.

The design should prioritize:

- PLA/PETG prototype parts, with final material selected according to mechanical demands.
- Standard metric fasteners.
- Existing MG90S and MG996R servo mounting geometry.
- Accessible servo horns.
- Small, printable linkage adapters.
- Minimal dependence on specialized machined components.
- Replaceable components rather than permanently bonded structures.

The designer should allow realistic manufacturing tolerances and avoid relying on perfect press fits.

The mechanism must be testable before silicone is installed.

## 10. Electronics Accommodation

The mechanical design does not need to include custom PCB design.

We plan to reuse two Will Cogley mouth PCBs:

- One for the existing mouth mechanism.
- One potentially repurposed for the eye and eyebrow mechanisms.

The skull should provide appropriate routing for servo leads and allow wiring to pass into the main electronics enclosure.

The electrical pinout and power distribution will be verified separately before integration.

The head will ultimately connect to a computer, speaker, microphone, and low-voltage power system housed primarily within the specimen base.

## 11. Required CAD Deliverables

### A. Complete Mechanical Skull Assembly
- Upper and lower skull structures
- Rear access panel
- Mounting points for existing Cogley modules
- Neck/base interface
- Cable routes
- Servo service clearances

### B. Eyebrow Mechanism
- Left and right eyebrow assemblies
- Servo mounts
- Curved brow carriers
- Pivots and connecting links, if needed
- Silicone attachment interfaces
- Assembly and exploded views

### C. Silicone Attachment System
- Miniature snap holders for moving linkages
- Interfaces compatible with existing Cogley lip endpoints
- Fixed perimeter attachment features
- Reinforced snap-pad positioning template
- Clearance and service-access analysis

### D. Sculpting and Mold Reference Geometry
- Outer facial proportion reference
- Skin clearance envelope
- Sculpting armature
- Alignment/registration features
- Skin attachment coordinate references

### E. Documentation
- Editable Onshape assembly
- STEP exports
- Print-ready STL files
- Hardware bill of materials
- Assembly instructions
- Servo motion/clearance notes
- Exploded diagrams
- Recommended print orientations

## 12. Proposed Design and Testing Milestones

**Milestone 1 — Mechanical Layout**

Import Cogley's mouth and EyeMech CAD. Establish overall proportions and verify that both mechanisms can coexist within a life-size skull.

**Milestone 2 — Eyebrow Prototype**

Develop and print the two eyebrow assemblies. Test their movement using MG90S servos.

**Milestone 3 — Integrated Skull**

Design and print the skull. Install the mouth, eye, and brow mechanisms and verify their full movement ranges.

**Milestone 4 — Snap Attachment Prototype**

Design the snap adapters. Cast small silicone samples containing reinforced snaps and test connection strength, movement, and removal.

**Milestone 5 — Sculpting Integration**

Prepare the registered skull/armature geometry and finalize facial proportions before physical sculpting.

**Milestone 6 — Silicone Skin Integration**

Fit the first cast silicone face, connect the moving attachment points, inspect deformation, and revise attachment placement where necessary.

**Milestone 7 — Final Mechanical Validation**

Test all facial movements with the silicone installed, confirm that linkages don't collide or overextend the skin, and verify that the face can be removed for maintenance.

## 13. Success Criteria

The mechanical design will be considered successful when:

- All existing mouth and eye mechanisms are securely integrated.
- Both eyebrows can move independently.
- No mechanical collisions occur throughout the intended motion ranges.
- The silicone face can be installed and removed without damaging the skin or mechanisms.
- Moving facial attachment points maintain their connections during repeated use.
- The silicone deforms convincingly without excessive bunching, visible hard points, or tearing.
- The entire structure can be assembled with standard tools.
- The skull is rigid, serviceable, and sufficiently compact for the future specimen enclosure.
- All custom parts can be fabricated using our available workshop equipment.

## 14. Design Priorities

In order of importance:

1. Reliable integration of existing mouth and eye mechanisms.
2. Natural-looking movement under silicone skin.
3. Reliable miniature snap attachments.
4. Serviceability and ease of assembly.
5. Compactness and printability.
6. Accurate facial proportions.
7. Compatibility with the sculpting and mold-making workflow.

The end goal is not simply to create a robot skull that moves.

**The goal is to create a mechanical foundation for a believable, expressive, conversational monster—one in which the internal mechanisms, silicone skin, and character design function as a single integrated system.**
