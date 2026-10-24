// Face boxes and face capture quality for images, using macOS's built-in Vision framework
// (no download, nothing leaves the Mac). Called by scripts/face_check.py.
//
//   swift scripts/face_boxes.swift a.png b.png ...
// prints one JSON object per image:
//   {"file": "...", "width": W, "height": H,
//    "faces": [{"x":..,"y":..,"w":..,"h":.., "confidence":.., "quality":..}]}
// Boxes are in pixels with the origin at the top-left. "quality" is Vision's face capture quality
// (0-1; lower for blur, bad lighting, odd pose or distortion); it is only meaningful when comparing
// faces of the same person.
import Foundation
import Vision

for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("{\"file\": \"\(path)\", \"error\": \"unreadable\"}")
        continue
    }
    let w = Double(img.width), h = Double(img.height)
    let rects = VNDetectFaceRectanglesRequest()
    let quality = VNDetectFaceCaptureQualityRequest()
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    do {
        try handler.perform([rects])
        let faces = rects.results ?? []
        quality.inputFaceObservations = faces
        try handler.perform([quality])
        let scored = quality.results ?? []
        var out: [[String: Double]] = []
        for (i, f) in faces.enumerated() {
            let b = f.boundingBox  // normalized, origin bottom-left
            var d: [String: Double] = [
                "x": b.minX * w, "y": (1 - b.maxY) * h, "w": b.width * w, "h": b.height * h,
                "confidence": Double(f.confidence),
            ]
            if i < scored.count, let q = scored[i].faceCaptureQuality { d["quality"] = Double(q) }
            out.append(d)
        }
        let obj: [String: Any] = ["file": path, "width": w, "height": h, "faces": out]
        let data = try JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])
        print(String(data: data, encoding: .utf8)!)
    } catch {
        print("{\"file\": \"\(path)\", \"error\": \"\(error.localizedDescription)\"}")
    }
}
