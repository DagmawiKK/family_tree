(Parent Adam Charles)
(Parent Beth Charles)
(Parent Adam Bebe)
(Parent Beth Bebe)
(Parent Adam Edward)
(Parent Beth Edward)
(Parent Adam George)
(Parent Beth George)

(Parent Charles Issac)
(Parent Diana Issac)
(Parent Charles Kevin)
(Parent Diana Kevin)

(Parent Edward Michael)
(Parent Fiona Michael)
(Parent Edward Oliver)
(Parent Fiona Oliver)

(Parent George Quentin)
(Parent Hannah Quentin)
(Parent George Samuel)
(Parent Hannah Samuel)
; 
(Parent Issac Ulysses)
(Parent Julia Ulysses)
(Parent Issac Victor)
(Parent Julia Victor)

(Parent Kevin William)
(Parent Laura William)
(Parent Kevin Xavier)
(Parent Laura Xavier)

(Parent Michael Yannis)
(Parent Nora Yannis)
(Parent Michael Zachary)
(Parent Nora Zachary)

(Parent Oliver Aaron)
(Parent Paula Aaron)
(Parent Oliver Benjamin)
(Parent Paula Benjamin)

(Parent Quentin Caleb)
(Parent Rachel Caleb)
(Parent Quentin Daniel)
(Parent Rachel Daniel)

(Parent Samuel Ethan)
(Parent Tina Ethan)
(Parent Samuel Frank)
(Parent Tina Frank)

(male Adam)
(female Beth)
(male Charles)
(female Bebe)
(male Edward)
(male George)
(female Diana)
(female Fiona)
(female Hannah)
(male Issac)
(female Julia)

(male Kevin)
(female Laura)

(male Michael)
(female Nora)

(male Oliver)
(female Paula)

(male Quentin)
(female Rachel)

(male Samuel)
(female Tina)
(male Ulysses)
(male Victor)

(male William)
(male Xavier)

(male Yannis)
(male Zachary)

(male Aaron)
(male Benjamin)

(male Caleb)
(male Daniel)

(male Ethan)
(male Frank)

(= (get-sex $x)
    (match &self ($sex $x) $sex)
)

(= (ans $x $acc) 
    (let*(
        ($parent (collapse (match &self (Parent $y $x) $y)))
    )
    (if (== $parent ())
        $acc
    (let $ans (match &self (Parent $y $x) $y) (let $sex (get-sex $ans) (let $newAcc (cons-atom ($ans $sex)  $acc) (ans $ans $newAcc))))
)))

; !(ans Issac ())
(= (decendants $x $acc) 
    (let*(
        ($parent (collapse (match &self (Parent $x $y) $y)))
    )
    (if (== $parent ())
        $acc
    (let $ans (match &self (Parent $x $y) $y) (let $sex (get-sex $ans) (let $newAcc (cons-atom ($ans $sex)  $acc) (decendants $ans $newAcc))))
)))

; !(Issac Charles ())

(= (sibilings $x)
   (let*(
        ($parents (match &self (Parent $p $x) $p))
        ($siblings (match &self (Parent $parents $sibil) $sibil))
        ($same (== $x $siblings))
    )   
    (if (== $same True)
        (empty)
        $siblings
    )
))

; !(sibilings Edward)
(= (children $x)
    (match &self (Parent $x $y) $y)
)

; !(children Adam)
(= (aunts-uncles $x) 
    (let*(
        ($parents  (collapse (match &self (Parent $p $x) $p)))
        (() (println! $parents))
        ($sibling (unique-atom (sibilings (superpose $parents))))
    )
    $sibling
    )
)


(= (aunts_or_uncles $x $sex) 
    (let*(
        ($parents  (collapse (match &self (Parent $p $x) $p)))
        ($sibling (unique-atom (sibilings (superpose $parents))))
    )
    (if (== (get-sex $sibling) $sex)
        $sibling
        (empty)
    )
    )
)
!(aunts_or_uncles Issac male)

(= (cousins $x)
    (let*(
        ($au (aunts-uncles $x))
        ($children  (unique-atom (children  $au)))
    )   
    $children
    )
)
; !(cousins M)

(= (sisters_or_brothers $x $sex)
    (let*(
        ($siblings (sibilings $x))
    )
    (if (== (get-sex $siblings) $sex)
        $siblings
        (empty)
    )
))

; !(sisters_or_brothers Charles male)