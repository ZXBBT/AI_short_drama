// Text and face landmarks in images, using macOS's built-in Vision framework (no download, nothing
// leaves the Mac). Called by scripts/take_checks.py (Stage 8: text-in-picture, eye contact, lip motion).
//
//   swift scripts/frame_checks.swift a.png b.png ...
// prints one JSON object per image:
//   {"file": "...", "width": W, "height": H,
//    "texts": [{"text": "...", "confidence": .., "x":.., "y":.., "w":.., "h":..}],
//    "faces": [{"x":..,"y":..,"w":..,"h":.., "yaw":.., "pitch":.., "roll":..,     (degrees, may be absent)
//               "left_eye": [[x,y],...], "right_eye": [...], "left_pupil": [x,y], "right_pupil": [x,y],
//               "inner_lips": [...], "outer_lips": [...]}]}
// All coordinates are pixels with the origin at the top-left.
import Foundation
import Vision

func deg(_ n: NSNumber?) -> Double? { n.map { $0.doubleValue * 180.0 / Double.pi } }

for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("{\"file\": \"\(path)\", \"error\": \"unreadable\"}")
        continue
    }
    let w = Double(img.width), h = Double(img.height)
    let size = CGSize(width: w, height: h)
    func pts(_ r: VNFaceLandmarkRegion2D?) -> [[Double]] {
        guard let r = r else { return [] }
        return r.pointsInImage(imageSize: size).map { [Double($0.x), h - Double($0.y)] }
    }
    let text = VNRecognizeTextRequest()
    text.recognitionLevel = .accurate
    text.usesLanguageCorrection = false  // report what is drawn, not a dictionary guess
    let rects = VNDetectFaceRectanglesRequest()
    rects.revision = VNDetectFaceRectanglesRequestRevision3  // continuous yaw/pitch/roll (the landmarks
    let marks = VNDetectFaceLandmarksRequest()               // request alone reports yaw in 45-degree steps)
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    do {
        try handler.perform([text, rects])
        marks.inputFaceObservations = rects.results ?? []
        try handler.perform([marks])
        var texts: [[String: Any]] = []
        for o in text.results ?? [] {
            guard let c = o.topCandidates(1).first else { continue }
            let b = o.boundingBox
            texts.append(["text": c.string, "confidence": Double(c.confidence),
                          "x": b.minX * w, "y": (1 - b.maxY) * h, "w": b.width * w, "h": b.height * h])
        }
        var faces: [[String: Any]] = []
        for f in marks.results ?? [] {
            let b = f.boundingBox
            var d: [String: Any] = ["x": b.minX * w, "y": (1 - b.maxY) * h, "w": b.width * w, "h": b.height * h]
            if let v = deg(f.yaw) { d["yaw"] = v }
            if let v = deg(f.pitch) { d["pitch"] = v }
            if let v = deg(f.roll) { d["roll"] = v }
            if let l = f.landmarks {
                d["left_eye"] = pts(l.leftEye); d["right_eye"] = pts(l.rightEye)
                d["inner_lips"] = pts(l.innerLips); d["outer_lips"] = pts(l.outerLips)
                if let p = pts(l.leftPupil).first { d["left_pupil"] = p }
                if let p = pts(l.rightPupil).first { d["right_pupil"] = p }
            }
            faces.append(d)
        }
        let obj: [String: Any] = ["file": path, "width": w, "height": h, "texts": texts, "faces": faces]
        let data = try JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])
        print(String(data: data, encoding: .utf8)!)
    } catch {
        print("{\"file\": \"\(path)\", \"error\": \"\(error.localizedDescription)\"}")
    }
}
